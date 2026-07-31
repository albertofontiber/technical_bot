-- s287 P2 — dedup a nivel DOCUMENTO: marca `duplicate_of` de los chunks GEMELOS
-- del doc no-representante. GENERADO read-only por scripts/s287_p2_dedup_census.py.
-- Spec: evals/s287_etapa2_design_brief_v1.md (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF Sol-6).
-- Census: evals/s287_p2_dedup_census_v1.json
-- Packet: evals/s287_p2_dedup_adjudicacion_packet_v1.md  ← LÉELO ANTES DE APROBAR NADA
--
-- ⚠ EDITADO A MANO tras la ADJUDICACIÓN COMPLETA de Alberto (s287) sobre los 24 pares.
--   Este fichero ya NO es salida limpia del generador, y `s287_p2_dedup_census.py` lo
--   SOBRESCRIBE (OUT_SQL, línea 104) → salva este .sql antes de re-correr el census.
--
-- ###########################################################################################
-- #  ESTADO DE LA ADJUDICACIÓN (Alberto, s287) — 24 pares repartidos en 5 clases:           #
-- #                                                                                          #
-- #   VIVOS  (3 pares · 12 marcas)   PAR 1 semilla + PAR 2 + PAR 14                          #
-- #   RECHAZADOS (10)  PAR 7·10·11·12·13·15·17·20·21·23 — productos/modelos DISTINTOS.       #
-- #                    Sus filas están FUERA de este paste; el ground truth de Alberto y     #
-- #                    la causa (metadata que los hizo indistinguibles) van en el packet §6. #
-- #   SUPERSEDED (2)   PAR 9 y PAR 22 — NO son dedup: son REVISIÓN NUEVA del mismo manual.   #
-- #                    Sus filas del census están FUERA (iban en la dirección CONTRARIA: el  #
-- #                    census proponía retirar chunks de la revisión NUEVA). El mecanismo    #
-- #                    de linaje va en el BLOQUE S al final, COMENTADO, pendiente de tu OK.  #
-- #   KEEP-BOTH (2)    PAR 8 y PAR 24 — doc_type distinto (usuario vs funcionamiento /       #
-- #                    instalación vs funcionamiento). Verificado en `documents`: el         #
-- #                    doc_type YA es correcto en los 4 docs → no hay fix que proponer.      #
-- #   ABIERTOS (7)     PAR 3·4·5·6·16·18·19 — preguntas de Alberto. Sus filas siguen         #
-- #                    COMENTADAS con mi propuesta inline; NADA de ellos entra hoy.          #
-- #                    Análisis con evidencia en el packet §8 «PREGUNTAS ABIERTAS».          #
-- #                                                                                          #
-- #  APROBAR UN PAR ABIERTO = quitar el '-- ' inicial de las filas de su bloque. No hay que  #
-- #  tocar comas: la fila SENTINELA cierra el VALUES.                                        #
-- ###########################################################################################
--
-- INVARIANTE del gate SPAN-DIFF (re-verificado en SQL, guard 3f): solo se marcan chunks de
-- clase TWIN — >= 0.92 de sus palabras cubiertas por el doc representante,
-- NINGUNA racha no cubierta de >= 25 palabras, y gemelo con
-- Jaccard >= 0.6. Los chunks UNIQUE / PARTIAL / COVERED_NO_TWIN / SHORT NO se
-- tocan: siguen sirviéndose desde el doc "suprimido" (la supresión es POR CHUNK, no por doc).
--
-- VIVO en este paste: PAR 1 (10 marcas) + PAR 2 (1) + PAR 14 (1) = **12 marcas**.
-- Los 8 guards de las 12 filas se RE-PRE-VALIDARON en vivo read-only contra la DB
-- (2026-07-30, posterior al census): 0 fallos — md5 sin deriva, ninguno ya marcado,
-- canónicos existentes/no-duplicados/dentro del representante, sin cadenas, gate 3f OK,
-- 0 filas de enunciados colgando. Dry-run esperado: **staged=12 · updated=12 · backed_up=12**.
-- Dry-run: cambia COMMIT por ROLLBACK.

BEGIN;
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- 0. METADATA-FIX del PAR SEMILLA · *** ADJUDICADO POR ALBERTO (s287): OPCIÓN B ***
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- El representante pasa a ser 'manual IS MA1' (doc B): la extracción MÁS COMPLETA (8 págs,
-- incluye el control drawing ATEX de p7-p8) y además la ISSUE MÁS NUEVA del mismo documento
-- de e2S — B dice "Document No. IS 5001  Issue H  03-01-2020" en las 6 hojas; A dice
-- "Issue F 06-08-15" en la portada y "Issue E 27-11-09" en las hojas 2-6. Criterio de
-- Alberto: «representante = la extracción más completa CON la metadata corregida; si la
-- metadata del más completo está corrupta, el fix va en el MISMO paste».
--
-- EVIDENCIA (sonda read-only 2026-07-30 contra la DB viva, cero escrituras):
--   · doc B `manufacturer='Detnov'` es ESPURIO — la cadena `detnov` no aparece en su propio
--     texto; su contenido dice "european safety systems ltd. impress house, mansell road,
--     acton, london w3 7qh" y "e2S". OJO: 66 documentos / 1409 chunks del corpus SÍ son
--     Detnov de verdad → todo UPDATE va acotado por document_id, nunca por valor.
--   · doc B `product_model`: 'unknown' a nivel doc y 'VIA-28V' en los 18 chunks. `VIA-28V`
--     es un ARTEFACTO DE PARSEO de la frase del manual "…designed to operate in a hazardous
--     area from a 24V dc supply VIA 28V 93mA resistive ATEX … Zener Barriers". Corpus-wide
--     `VIA-28V` existe SOLO aquí (18 chunks, 0 documents) → el fix no puede tocar nada más.
--   · doc A `product_model='IS5001'` a nivel doc es la REFERENCIA DEL MANUAL, no el producto:
--     el pie de página de LOS DOS docs dice "Document No. IS 5001". Sus 15 chunks ya llevan
--     'IS-mA1' (correcto) → A también entra en el fix, solo a nivel `documents`.
--   · MODELO CORRECTO = IS-mA1: la portada de AMBOS docs dice "INSTRUCTION MANUAL / IS-mA1
--     Minialarm / Intrinsically Safe Round Sounder" y la placa ATEX de ambos, "IS-mA1 Sounder".
--
-- GUARD: mismo patrón que el 3a — la precondición viaja EN el paste y ABORTA si el estado
-- vivo no es el que vio la sonda. Aquí el valor literal ES el hash (son campos cortos, no
-- blobs): comparar el literal es la forma más fuerte y legible del mismo control.
-- Este bloque 0 es INDEPENDIENTE del 4: si retiras el par semilla, comenta el bloque entero.

-- 0.1 BACKUP (persistente, para rollback post-COMMIT)
CREATE TABLE IF NOT EXISTS _s287_metafix_backup_documents AS
SELECT id, manufacturer, product_model, now() AS backed_at
FROM documents
WHERE id IN ('a6b9dc84-af6d-4957-a403-4b4c2136557b',
             '2b694083-5b21-4f1a-a29b-565072860fb8');

CREATE TABLE IF NOT EXISTS _s287_metafix_backup_chunks AS
SELECT id, document_id, manufacturer, product_model, now() AS backed_at
FROM chunks_v2
WHERE document_id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b';

-- 0.2 GUARDS de precondición (cualquiera aborta TODO)
DO $$
DECLARE m int;
BEGIN
  -- 0a. doc B activo y con EXACTAMENTE la metadata corrupta que vio la sonda
  SELECT count(*) INTO m FROM documents
   WHERE id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b' AND status = 'active'
     AND manufacturer = 'Detnov' AND product_model = 'unknown';
  IF m <> 1 THEN RAISE EXCEPTION
    'doc B no está en el estado pre-fix esperado (Detnov/unknown) — ABORTA'; END IF;

  -- 0b. doc A activo y con EXACTAMENTE el pm doc-level a corregir
  SELECT count(*) INTO m FROM documents
   WHERE id = '2b694083-5b21-4f1a-a29b-565072860fb8' AND status = 'active'
     AND manufacturer = 'European Safety Systems' AND product_model = 'IS5001';
  IF m <> 1 THEN RAISE EXCEPTION
    'doc A no está en el estado pre-fix esperado (European Safety Systems/IS5001) — ABORTA'; END IF;

  -- 0c. los 18 chunks de B llevan TODOS el artefacto, y nada fuera de B lo lleva
  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b';
  IF m <> 18 THEN RAISE EXCEPTION 'doc B tiene % chunks, la sonda vio 18 — ABORTA', m; END IF;

  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b'
     AND product_model = 'VIA-28V' AND manufacturer = 'Detnov';
  IF m <> 18 THEN RAISE EXCEPTION
    'solo % de los 18 chunks de B están en el estado pre-fix (VIA-28V/Detnov) — ABORTA', m; END IF;

  SELECT count(*) INTO m FROM chunks_v2
   WHERE product_model = 'VIA-28V'
     AND document_id <> 'a6b9dc84-af6d-4957-a403-4b4c2136557b';
  IF m > 0 THEN RAISE EXCEPTION
    'VIA-28V aparece en % chunks FUERA del doc B — la sonda vio 0, revisa antes de tocar', m; END IF;

  -- 0d. el doc A ya tiene el pm correcto a nivel chunk (no se toca)
  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id = '2b694083-5b21-4f1a-a29b-565072860fb8'
     AND product_model = 'IS-mA1' AND manufacturer = 'European Safety Systems';
  IF m <> 15 THEN RAISE EXCEPTION
    'los chunks de A no están como los vio la sonda (15× IS-mA1/European Safety Systems) — ABORTA'; END IF;
END $$;

-- 0.3 UPDATES (5 campos · SIEMPRE acotados por document_id)
UPDATE documents SET manufacturer = 'European Safety Systems'          -- (1) B doc-level manu
 WHERE id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b' AND manufacturer = 'Detnov';

UPDATE documents SET product_model = 'IS-mA1'                          -- (2) B doc-level pm
 WHERE id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b' AND product_model = 'unknown';

UPDATE chunks_v2 SET product_model = 'IS-mA1'                          -- (3) B chunk-level pm
 WHERE document_id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b' AND product_model = 'VIA-28V';

UPDATE documents SET product_model = 'IS-mA1'                          -- (4) A doc-level pm
 WHERE id = '2b694083-5b21-4f1a-a29b-565072860fb8' AND product_model = 'IS5001';

-- (5) AÑADIDO por la sonda, NO estaba en la lista de 4 campos — decláralo o coméntalo:
--     los 18 chunks de B llevan manufacturer='Detnov' a nivel CHUNK, y ese es el campo que
--     FILTRA de verdad (`match_chunks_v2(filter_manufacturer)` compara `c.manufacturer`,
--     supabase_schema.sql:81). Dejarlo sin tocar mantendría al representante nuevo sirviendo
--     los hechos de cat010 etiquetados 'Detnov' — justo el defecto que motivó la opción B.
UPDATE chunks_v2 SET manufacturer = 'European Safety Systems'          -- (5) B chunk-level manu
 WHERE document_id = 'a6b9dc84-af6d-4957-a403-4b4c2136557b' AND manufacturer = 'Detnov';

-- 0.4 POST-CHECK del fix (aborta si algún campo quedó a medias)
DO $$
DECLARE m int;
BEGIN
  -- campos (1)(2)(4): los DOS documents con manufacturer y pm correctos
  SELECT count(*) INTO m FROM documents
   WHERE id IN ('a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8')
     AND manufacturer = 'European Safety Systems' AND product_model = 'IS-mA1';
  IF m <> 2 THEN RAISE EXCEPTION 'metadata-fix doc-level incompleto (% de 2) — ABORTA', m; END IF;

  -- campo (3): 18 chunks de B + 15 de A = 33 con el pm correcto
  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id IN ('a6b9dc84-af6d-4957-a403-4b4c2136557b',
                         '2b694083-5b21-4f1a-a29b-565072860fb8')
     AND product_model = 'IS-mA1';
  IF m <> 33 THEN RAISE EXCEPTION 'metadata-fix pm chunk-level incompleto (% de 33) — ABORTA', m; END IF;
END $$;

-- Check del campo (5) — EN SU PROPIO BLOQUE: si comentas el UPDATE (5), comenta también esto.
DO $$
DECLARE m int;
BEGIN
  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id IN ('a6b9dc84-af6d-4957-a403-4b4c2136557b',
                         '2b694083-5b21-4f1a-a29b-565072860fb8')
     AND manufacturer = 'European Safety Systems';
  IF m <> 33 THEN RAISE EXCEPTION
    'metadata-fix manufacturer chunk-level incompleto (% de 33) — ABORTA', m; END IF;
END $$;
-- SIN EFECTOS COLATERALES verificados: el trigger FTS `chunks_v2_search_vector_trigger` es
-- `BEFORE INSERT OR UPDATE OF content, context, section_title, section_path`
-- (migrations/006_chunks_v2.sql:181-186) → NO dispara con product_model/manufacturer. Y el
-- `context` de los 18 chunks de B NO contiene 'VIA-28V' ni 'Detnov' (sonda) → el artefacto
-- no está embebido en el texto que se indexa ni se embebe.
-- RESIDUAL DECLARADO (no se toca aquí): `chunks_v2_hyq` guarda una copia DESNORMALIZADA de
-- product_model/source_file — 49 filas de B siguen diciendo 'VIA-28V'. Es INERTE para el
-- servicio: `match_hyq` devuelve solo (chunk_id, question, similarity) y el retriever
-- rehidrata desde chunks_v2 (retriever.py:1091, _HYDRATE_SELECT). Queda anotado para que no
-- se pudra en silencio; incluirlo sería 1 UPDATE más si quieres consistencia total.


-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- 0-bis. METADATA-FIX CANDIDATO del representante del PAR 2  ***COMENTADO — REQUIERE TU OK***
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- Decisión 2 del PAR 2 (metadata del representante). Sonda read-only 2026-07-30:
--   'DXc_Connexion Averia-de-resistencia-de-baterias.pdf' (5e878ee7) → documents.product_model
--   = 'unknown' pero su único chunk dice pm='DXc', y el TÍTULO del propio contenido es
--   «Tengo avería de resistencia de baterías en central DXc» → el valor bueno está en el chunk.
-- Política confirmada por Alberto (s287): las divergencias documents↔chunks se adjudican
-- POR-DOC contra la portada. Aquí no hay portada (es un FAQ de 1 chunk) pero el título del
-- propio texto nombra el producto → candidato SÓLIDO, no automático. Sale COMENTADO porque
-- Alberto adjudicó el DEDUP del par 2, no su metadata.  (Va también al ticket A3.)
--
-- DO $$
-- DECLARE m int;
-- BEGIN
--   SELECT count(*) INTO m FROM documents
--    WHERE id = '5e878ee7-53eb-4b03-bda3-5fd5de306bba' AND status = 'active'
--      AND manufacturer = 'Morley' AND product_model = 'unknown';
--   IF m <> 1 THEN RAISE EXCEPTION 'par 2: doc representante no está en el estado pre-fix — ABORTA'; END IF;
--   SELECT count(*) INTO m FROM chunks_v2
--    WHERE document_id = '5e878ee7-53eb-4b03-bda3-5fd5de306bba' AND product_model = 'DXc';
--   IF m <> 1 THEN RAISE EXCEPTION 'par 2: el chunk no dice DXc (% filas) — ABORTA', m; END IF;
-- END $$;
-- UPDATE documents SET product_model = 'DXc'
--  WHERE id = '5e878ee7-53eb-4b03-bda3-5fd5de306bba' AND product_model = 'unknown';

-- 1. STAGING (scratch; el paste la crea y la puebla — no hay carga previa)
DROP TABLE IF EXISTS _s287_dedup_staging;
CREATE TABLE _s287_dedup_staging (
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

-- Cada fila real termina en coma y la última fila del VALUES es la SENTINELA (sin coma) →
-- puedes descomentar CUALQUIER subconjunto de bloques sin tocar comas.
INSERT INTO _s287_dedup_staging
 (chunk_id, canonical_chunk_id, doc_suppressed, doc_representative,
  covered_word_frac, twin_jaccard, max_uncovered_span_words, md5_content_before, pair_id)
VALUES
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 1: 2b694083__a6b9dc84   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** PAR SEMILLA (cat010) ***
--   *** ADJUDICADO POR ALBERTO (s287) → OPCIÓN B · DIRECCIÓN INVERTIDA · SIN CASILLA ***
--   CONSERVA  'manual IS MA1'      (doc B · 18 chunks · 8 págs · Issue H 03-01-2020)
--             metadata CORREGIDA en el bloque 0 de este mismo paste
--   SUPRIME   10 de 15 chunks de 'IS5001-F_IS-mA1_EN'  (doc A · Issue F/E 2015-2009)
--   PRESERVA  PARTIAL=5 de A (idx 0,5,7,8,9) + los 18 chunks de B intactos
--   cobertura 0.89 (A cubierto por B) / 0.72 (B cubierto por A)
--   MOTIVO: doc canónico completo por manual físico (Alberto) — B tiene el control drawing
--           ATEX de p7-p8 (los 4 chunks UNIQUE, territorio de los hechos de cat010) y es la
--           ISSUE MÁS NUEVA del mismo Document No. IS 5001.
--
--   ¡OJO! 10 marcas, no 9. La clase TWIN es DIRECCIONAL y se re-clasifica al invertir: el
--   census ya midió `side_a.classes = {TWIN: 10, PARTIAL: 5}`. Los 9 punteros del sentido
--   viejo invertidos son un SUBCONJUNTO; el que falta es el chunk idx2 de A (77003e0f), TWIN
--   en esta dirección (cov 0.9325, racha 0, J 0.6351 con 77a0cce8) y que en el sentido
--   antiguo no salía porque su gemelo 77a0cce8 es PARTIAL en B (cov 0.9061 < 0.92).
--   Los `covered_word_frac` / `max_uncovered_span_words` de abajo son los del lado A
--   (dirección nueva), NO los reciclados del lado B — reciclarlos habría dejado el guard 3f
--   validando números de otro chunk. `twin_jaccard` sí es simétrico.
--   Si prefieres la inversión literal de 9, comenta SOLO la fila marcada `[+1]`.
  ('d4ae732f-2838-4134-a558-680b1ac36bb8','25d7fd21-e168-43e4-b2e6-b73b15aff49d','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9693,0.7444,0,'862dcdcbc5a024b6a8e1ea48fe735815','2b694083__a6b9dc84'),   -- idx1 p1 424w · 4.1 ATEX certificate
  ('77003e0f-fbaa-4def-adc3-cbf7cc000683','77a0cce8-b238-4507-a4ab-17491badfe0c','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9325,0.6351,0,'6364787451a49c7007eeeb0bf4a0c86e','2b694083__a6b9dc84'),   -- idx2 p2 504w · [+1] TWIN solo en esta dirección
  ('1a7ac511-31fd-4281-a482-157c3dabcb15','68c40b6f-c4a4-478e-adff-bf32febc2cd7','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9873,0.7157,0,'1443272a951c843e3a6b1d02fef462ee','2b694083__a6b9dc84'),   -- idx3 p2 157w · 4.1 ATEX certificate
  ('2b9a9f41-f468-42db-895b-920fb5050472','b21ff3e2-56f0-4d12-96d9-6735f6648a7c','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9766,0.8022,0,'69181b5301f58e01c9bf5304dcb71285','2b694083__a6b9dc84'),   -- idx4 p3 896w · 4.1 ATEX certificate
  ('9d4ae236-ad66-428e-91b2-5fd254715b23','1ffd36f5-2f6d-4759-aac5-e1cf532833da','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',1.0,1.0,0,'60db8eb69268cf462eba150b808b0270','2b694083__a6b9dc84'),   -- idx6 p4 310w · J=1.000
  ('c07ed164-df92-4e07-9e8a-d1a4d730d3f0','e3a101aa-41dd-4aa1-a042-1b7b01bcf467','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',1.0,1.0,0,'7276f8f9892f36fe059b6cef63171caf','2b694083__a6b9dc84'),   -- idx10 p5 79w · J=1.000
  ('d4e91d5f-2721-45bb-8cbb-ca7fbbdd9fc9','70f4ac0e-1497-460a-b893-4bcfd33f0168','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9545,0.8261,0,'69615a3c9f14cb9a558d15180605f2d3','2b694083__a6b9dc84'),   -- idx11 p5 154w
  ('4feea9a8-59d3-4742-9ab9-2ff9aee1caa0','ba38fed9-e1a9-4388-941e-78de2289e27a','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9553,0.7052,0,'ef0019fb43549e38f1ce956d126f98d6','2b694083__a6b9dc84'),   -- idx12 p6 403w · IECEx Approval
  ('e10519a0-e237-49df-a151-83a859609a8e','df475873-b2d4-4884-9086-a527771a3f82','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',0.9921,0.6642,0,'20684fdaba29f3a3d3a4d8c7fae8890e','2b694083__a6b9dc84'),   -- idx13 p6 126w · FM Approval
  ('7eff6257-85e6-402d-9947-90c7336ff7e1','d335a010-5715-4214-975b-1e18bf58ac75','2b694083-5b21-4f1a-a29b-565072860fb8','a6b9dc84-af6d-4957-a403-4b4c2136557b',1.0,1.0,0,'06911258051b6a2704b035aec059acf7','2b694083__a6b9dc84'),   -- idx14 p6 124w · CPD 89/106/EEC · J=1.000
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 2: 5e878ee7__eb749df8   [T1-DOC-IDENTICO]   *** APROBADO POR ALBERTO (s287) — VIVO ***
--   CONSERVA  'DXc_Connexion Averia-de-resistencia-de-baterias.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   1 de 1 chunks de 'Averia-de-resistencia-de-baterias-en-central-DXc.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  (nada más en el doc suprimido)
--   cobertura 0.95/0.96 · motivo del representante: empate → más reciente (revision_date/revision/ingested_at)
--   VEREDICTO Alberto: OK (duplicado real: el mismo FAQ del DXc subido dos veces con
--   el título reordenado). Contenido verificado idéntico en la sonda read-only.
--   Decisión 2 (metadata del representante): candidato pm 'unknown'→'DXc' en el bloque 0-bis.
--   GUARDS RE-PRE-VALIDADOS EN VIVO (read-only, 2026-07-30): md5 sin deriva · no marcado ·
--   canónico existente/no-duplicado/dentro del representante · sin cadenas · gate 3f OK ·
--   0 filas de enunciados colgando.
  ('f58ad5cd-5d6a-438f-b546-4ff11d5b8b48','c9952764-8b68-4aea-b7ca-9d6a85fa917c','eb749df8-87db-4800-90dd-7d65889822fa','5e878ee7-53eb-4b03-bda3-5fd5de306bba',0.9536,0.7803,0,'fa4905b168fc4c5225f9c099ef755a99','5e878ee7__eb749df8'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 3: 517b87ce__de8c0345   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'FS2-1'  (manu='Notifier' pm='FS2-1')
--   SUPRIME   12 de 27 chunks de 'ms1-2-4.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=4, PARTIAL=5, COVERED_NO_TWIN=6
--   cobertura 0.80/0.86 · motivo del representante: metadata auto-soportada (2/3 vs 0/3)
--   ⏸ PREGUNTA ABIERTA de Alberto («¿no son muy similares?») — packet §8.1.
--   MI PROPUESTA: **NO deduplicar** (rebadge OEM). Los dos son el MISMO manual rebadgeado:
--   FS2-1 imprime «NOTIFIER ESPAÑA, S.L.» y nombra FS-1/FS-2/FS-4; ms1-2-4 es «Ref. 997-158
--   Versión 1.0, 9 Enero 2002» y nombra MS-1/MS-2/MS-4. Verificado: los 7 chunks TWIN que se
--   propone retirar nombran MS-1/MS-2/MS-4 y su gemelo nombra FS-1/FS-2/FS-4 → deduplicar
--   haría que el bot responda una pregunta de MS-2 citando el manual de FS-2 (daño DEC-091b).
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('3f117e9e-da69-474d-932d-094349d7ced5','3a16fb38-1f65-4d6e-9f3f-e310e053f3a6','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.983,0.9399,0,'3d3e092c996889bafb75023787ed92ef','517b87ce__de8c0345'),
--   ('6cad07bc-fd6d-4efb-9dcc-acc4f5c66bb9','79726dcc-0144-4e9d-a0f5-43c7742488da','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9912,0.8462,0,'aeb5cf04d547ba1f1c17c6ebef9160ef','517b87ce__de8c0345'),
--   ('4a2cd170-c906-4ae1-8bc7-3718288d8a52','b8bc8a99-cc64-44c7-91e0-c0259438dbe7','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9586,0.77,0,'9d94e64c2f3fb75d010a24a788d91400','517b87ce__de8c0345'),
--   ('eaca7e7a-0514-479b-b727-85a1bcdc7271','9a3b5583-6cbd-4858-b35e-6d0f51f38e25','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.971,0.7758,0,'b7b3e4f6b23ec5d3522c79fc45ceedbc','517b87ce__de8c0345'),
--   ('a94a7818-b95b-4774-9646-61bd42990e6c','e6bce97f-0a30-430f-ba2b-e4c28202655b','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9903,0.95,0,'e3713ca6a85d6b2907da72490c50c3e5','517b87ce__de8c0345'),
--   ('3f82fd8c-c111-43fd-9e6a-b598b7d487d7','8f2d1255-d5ae-42d1-b9c1-dab0925ec8e0','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9886,0.9683,0,'6138a4fd219af72d35969c85aeb74f05','517b87ce__de8c0345'),
--   ('b116703f-b3e5-461b-a89a-84b0a6abebc7','bae2998e-c033-4836-9355-7683b3015510','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9674,0.8184,0,'452665c82967dc79667c55bba1ebd8ad','517b87ce__de8c0345'),
--   ('d199d06f-7be8-4b06-80aa-df88a5a2a3c3','02975fd0-8db4-4b3b-ac6d-71130f7c4cfa','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9569,0.6763,0,'e78dc0367ecdc5227d3dad631542c817','517b87ce__de8c0345'),
--   ('19f38f8f-9b72-4a3b-b91f-37bba61245ce','d0496d31-6589-4944-8be3-9e8113e14700','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.987,0.6622,0,'d6f169750ef595ded0f1c882300a4e24','517b87ce__de8c0345'),
--   ('4e141903-029c-4b2c-ab7e-3e803ae8c3bf','57c01d50-245c-4288-8851-924786332b4d','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9953,0.9263,0,'bede104c39179436e336de6ef0270465','517b87ce__de8c0345'),
--   ('dbb5fdd1-0f84-4dd6-9dc9-8b7e811d0d8e','6172917e-70ef-45fe-8673-77f8523e4300','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9645,0.8356,0,'e909a50f51cc901aab360aeb7b43f8cc','517b87ce__de8c0345'),
--   ('f52d2fc3-89c1-4687-ae4d-cc85538b49ea','e872a4f9-1b11-4185-89cb-b7bb8781d0a4','de8c0345-2b30-4cfa-a73c-968038acde1f','517b87ce-500b-4e43-a32a-ad6c96b7d4eb',0.9834,0.9116,0,'a08def76915d21c8650b6f4b74823558','517b87ce__de8c0345'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 4: 7f9ea4ab__acafc5d1   [T2-MISMA-MARCA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'MNDT1026'  (manu='Notifier' pm='VIEW')
--   SUPRIME   5 de 23 chunks de 'MNDT1025'  (manu='Notifier' pm='VIEW')
--   PRESERVA  UNIQUE=3, PARTIAL=12, COVERED_NO_TWIN=3
--   cobertura 0.64/0.85 · motivo del representante: empate metadata → más spans únicos (18 vs 8)
--   ⏸ PREGUNTA ABIERTA de Alberto (¿1026 más completo? ¿1025 tiene algo único?) — packet §8.2.
--   VERIFICADO: MNDT1026 = «Aplicaciones del VIEW™ CON LA CENTRAL AFP-300/400» (MN-DT-1026_A,
--   24 MAR 2004); MNDT1025 = «Aplicaciones del VIEW™» genérico (MN-DT-1025, 8 ABR 2004,
--   doc. 997-198). 1026 SÍ es más completo (secciones propias: Cableado · Programación de la
--   cooperación · Autoaprendizaje de prealarma · Algoritmos de filtrado). De lo ÚNICO de 1025
--   (412 palabras en 8 spans) no sale ningún HECHO nuevo: son prosa de figura/tabla ASCII.
--   MI PROPUESTA: aprobable con riesgo bajo (mismo producto, mismo fabricante). Residual
--   declarado: 1025 etiqueta sus chunks pm='FSL-751E' y 1026 pm='VIEW' → retirar 5 chunks
--   reduce el alcance de la etiqueta 'FSL-751E' (candidato de unificación al ticket A3).
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('130b656a-2ad3-4025-b2bd-7768f46bfacf','a4bcff6e-b2e8-4328-b677-0048da277226','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9915,0.8413,0,'3a92eced40884313b187a82a35431c84','7f9ea4ab__acafc5d1'),
--   ('6def4121-4b61-4737-aba0-e2e488dce100','3d792de5-1b05-4028-b2c2-a2942f9267f6','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9912,0.8522,0,'80d7733541322e0105f98c7de9c290eb','7f9ea4ab__acafc5d1'),
--   ('effaf7c3-413d-4b94-a0d4-7acfde4395fb','6d29d2d8-d34b-4599-a7ca-c118d54a12d7','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9764,0.8617,0,'d4516629a79407f1f286e7df176afb51','7f9ea4ab__acafc5d1'),
--   ('ac8027dc-9c00-4ca5-a89d-7563ab84573f','ae1a68ce-3b87-4699-bd20-4bf3713ea238','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9523,0.6755,0,'cf4cfd643f4405a32a674af1526b9ff3','7f9ea4ab__acafc5d1'),
--   ('685ab164-fac2-41be-ab86-febe0ff66059','d245c6fb-aa4c-40bb-b6b5-1fce2137d302','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.952,0.7912,0,'a0a0cc249800e60cafa252169e33106e','7f9ea4ab__acafc5d1'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 5: 5800c4c0__cbc9c21c   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'FS8'  (manu='Notifier' pm='EFS/EM 8')
--   SUPRIME   30 de 63 chunks de 'MS8.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=8, PARTIAL=20, COVERED_NO_TWIN=5
--   cobertura 0.84/0.85 · motivo del representante: metadata auto-soportada (1/3 vs 0/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'MS8.pdf' (más spans únicos (36 vs 27))
--   ⏸ PREGUNTA ABIERTA de Alberto («exactamente el mismo documento») — packet §8.3.
--   CONFIRMADO: es el MISMO documento. Las dos portadas dicen «Panel de control de incendios
--   de 8 zonas EFS/EM 8 · Manual de instalación, puesta en marcha y funcionamiento ·
--   997-201-103 · Edición 1, Septiembre 1999». Ninguno de los dos imprime Notifier NI Morley
--   en su texto: la atribución de marca es SOLO metadata. Los spans 'UNIQUE' de ambos lados
--   son la MISMA sección extraída dos veces (mutuos best-twin) — verificado que 8.7.1 y 3.4.4
--   existen en LOS DOS. MI PROPUESTA: **no aprobar tal cual**. Retirar 30 de los 63 chunks
--   etiquetados 'Morley' degrada el alcance por marca de un manual que es de marca DUAL
--   (EFS = Notifier / EM = Morley). Primero decidir el seam de identidad (D1/D3), luego dedup.
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('c1523563-cecb-4250-9b37-abbac4834a69','2e01c2f0-b979-47f8-ab35-e9517d287c55','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9978,0.9438,0,'3b18b88ca3120d573348b14e1580cfbc','5800c4c0__cbc9c21c'),
--   ('ac4a3c5e-3f13-4457-8e25-5a610b683f18','2f353ee0-b4d5-496d-957f-4fd89c93dde9','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'85f571669e91d3d9ebe77a34c66f0996','5800c4c0__cbc9c21c'),
--   ('8aa4242d-8cf7-4d42-97f2-46bab036a6f8','31ac73de-78f2-4776-87b4-8037990eb92b','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,0.6923,0,'c1015e9dcd6136dbb99950dfc5b79ddd','5800c4c0__cbc9c21c'),
--   ('0347737c-026c-493a-b6b1-53638396dc76','1c46765d-35f7-4731-9b81-a764b048796b','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9967,0.8322,0,'6cb40718a89c9a223b0a54e309e56e00','5800c4c0__cbc9c21c'),
--   ('7f2e8856-1c3b-47c0-8256-bf20d225ce86','cb390e4a-34b9-43d1-910c-6f85830831b6','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9835,0.8537,0,'efe4ec3c8d6ad17ef886bf83d5f4e5fc','5800c4c0__cbc9c21c'),
--   ('e56f7e86-6695-4bcc-bd45-debba780eb9e','4f82e262-88d1-4cf2-8529-9f3d031a6368','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9543,0.7852,0,'0e68d9600dcc13726c6fd090158825c9','5800c4c0__cbc9c21c'),
--   ('681a53dd-893e-41b2-8a23-a2bd288284af','cb475571-02ae-47d1-b123-199137e0528c','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'590ebf9299c0b87b2465a98527152742','5800c4c0__cbc9c21c'),
--   ('7a928f0e-a5c0-4795-b05c-79e7a164e112','0d1eaf10-488c-4bf5-8c32-50d528b75bc9','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'95fc06e6a37d18997b7c3399ca41405c','5800c4c0__cbc9c21c'),
--   ('fe1412e4-f8e3-4f50-893c-a8b62d9262d5','14cfed89-7f10-45f4-a2da-364c2eea3fbd','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'83bad52159757875a7babc3368b7166a','5800c4c0__cbc9c21c'),
--   ('d741bdc2-5108-4337-86c6-6db2811a2e71','2308c212-256f-4b8b-8500-db92da4e2d22','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'c55a1f21f3fb1db580e69005c84e76f3','5800c4c0__cbc9c21c'),
--   ('8fd58bba-2c0a-40ae-821a-3ddc3d38c40e','2cdeaee3-61ff-45c3-ace0-d2ebff626ea8','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'0929d1f46cdfbd425f7b1b769942cf8b','5800c4c0__cbc9c21c'),
--   ('ee88c4db-3bc8-40e3-92c9-d7f770a802cf','38827df2-7791-4914-bef3-befca139c445','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9789,0.8849,0,'49a3218bbf90ea60c280a977296abacf','5800c4c0__cbc9c21c'),
--   ('c27ded6e-7e94-4480-8e83-36e95a2b9b5d','af8142dc-777d-4ee3-89ad-dc69b21e700f','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'897640d6dd95fd0356077e04a8812782','5800c4c0__cbc9c21c'),
--   ('77b5ef78-faba-4e59-ba53-a76f8aa092fc','a9cc20b1-cb3f-45e1-b9f3-98108c129c65','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9719,0.8927,0,'052dce2f85f3fcc0280ebc850017624b','5800c4c0__cbc9c21c'),
--   ('f4a1f1af-c870-4aa2-9ec5-b2ae2d65173d','4d73ebe1-65fc-47c3-abe9-0c306b65ec81','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9249,0.6893,0,'0b9270cc477c735da614789af1c79370','5800c4c0__cbc9c21c'),
--   ('e6947167-f79e-4194-bc4f-b3c4e3688005','c6676813-1b16-4772-8a31-ddbb23772412','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9791,0.9694,0,'a27fabb36b897e14c671f437be007a4c','5800c4c0__cbc9c21c'),
--   ('f07853ee-1405-4d02-84f0-8a8e5568a91c','666a997c-858f-47a1-8bc8-3da22b198236','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'5a87afe1c6f668f18a4582e03184eac3','5800c4c0__cbc9c21c'),
--   ('4a4ebb6f-bbd0-4501-be5d-1f65ffe03597','1eb5f6d5-00bb-4da7-8ee7-597cb00d3c2a','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'88821971d5214a975d605183c97174ae','5800c4c0__cbc9c21c'),
--   ('1a7d2036-9fa8-440d-883e-0b48df6ce6cc','ce1cee1a-0905-4477-88d6-1960bfa53b8a','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'8106ed1c00f0b4b4218929e97ebefb0f','5800c4c0__cbc9c21c'),
--   ('344ff5a5-1f21-4238-912b-c45ceae69a92','714c4ee6-3e40-42c5-b685-ab4d45f7196f','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'a59e034c6cdf20bf01eb8b05debb8035','5800c4c0__cbc9c21c'),
--   ('c3d59524-c15f-4f6a-a37a-5161f310a372','c8981ad0-fe8c-429d-bb59-9c6a343fe368','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'ce7897069bc2c6a27f2aa8445eebe7c5','5800c4c0__cbc9c21c'),
--   ('076d50cd-c27e-4169-bcc1-5c90b7ba416b','5f0634c6-2a7f-4628-af69-0a9e1e92364d','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,0.7778,0,'8f1524d5219cbf13f297a11b78382966','5800c4c0__cbc9c21c'),
--   ('cc28922d-70b9-4463-bce0-88ec9f048bc3','fe5b6772-384c-448e-b418-f9c3230cf68c','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9922,0.9837,0,'a5c6cd810173919c115635a7568da66c','5800c4c0__cbc9c21c'),
--   ('9c9a3387-0f30-4e3b-b7b3-7f57782b86f2','7344f13e-d868-4a74-8e9b-ad4c418c6270','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9954,0.9906,0,'222d929f49455ab62b40969d35363a56','5800c4c0__cbc9c21c'),
--   ('d61a3697-43d3-4ecf-89fc-a31c3b55562c','a7f528b1-3594-4848-9ce3-e3ee82a96d25','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.94,0.7921,0,'ef0e867d600a6db7cd25bd5cdd28be85','5800c4c0__cbc9c21c'),
--   ('7435e789-35d4-4f57-805f-08a89dcc71d2','6ad17196-368d-4b87-952b-f2f903f6aa38','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,0.7835,0,'48282ebe7c8c615ddce5e9a181c5354f','5800c4c0__cbc9c21c'),
--   ('39ef1e3d-8f0e-4598-85df-cdd14d4afbb2','7002ce87-f84f-4219-8695-a7c4b7dd3ed3','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.978,0.6888,0,'0e417d2c04b6f94c244261d9d8319159','5800c4c0__cbc9c21c'),
--   ('7e198f07-295e-4a4b-9344-993cc0857a40','f599b8b2-d4e5-4684-9bef-337c628f4fbc','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',0.9932,0.7985,0,'7e40bfcba0face750f27f5354a2c21d0','5800c4c0__cbc9c21c'),
--   ('17ba332d-dffe-4c45-8d26-3d50bc2acf3c','205c093b-e9ac-46ac-9780-74984457b724','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,0.6034,0,'fd18162b1d6893cef6de1e2cf54a3417','5800c4c0__cbc9c21c'),
--   ('1513b3ac-3507-4d57-b076-71ff778e83b9','da1931be-e37d-4ca7-927b-48ccb43c5797','cbc9c21c-4369-4316-905f-40cdce16af53','5800c4c0-df50-46c0-b37b-a756417e7131',1.0,1.0,0,'c392d95ebe4acb248ad2efd5fdace319','5800c4c0__cbc9c21c'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 6: 2c299ef1__89024b18   [T2-MISMA-MARCA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'D 1148-1 BRS Notifier'  (manu='Notifier' pm='B501AP')
--   SUPRIME   2 de 7 chunks de 'D 1147-1 BRH Notifier'  (manu='Notifier' pm='B501AP')
--   PRESERVA  UNIQUE=2, PARTIAL=2, COVERED_NO_TWIN=1
--   cobertura 0.80/0.83 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   ⏸ PREGUNTA ABIERTA de Alberto («exactamente el mismo documento») — packet §8.4.
--   NO se confirma: son datasheets de productos DISTINTOS. D 1148-1 BRS → pm de chunk 'SP-20',
--   I(max) 25/14 mA, P 590/330 mW, remite a SP20-3249. D 1147-1 BRH → pm 'NFXI-BSF-WCH',
--   I(max) 32/24/13 mA, P 760/580/320 mW, remite a SP20-3248. Y el chunk grande que se
--   propone retirar es la TABLA DE TONOS: la del BRH es «Default Setting (C-3-15)» y la
--   cadena 'C-3-15' aparece 3× en el BRH y **0× en el BRS** → retirarlo borra el ajuste por
--   defecto del BRH. MI PROPUESTA: **RECHAZAR** (keep-both).
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('f0154a63-652c-4748-a9fb-a082a4e4b160','1416c36a-2d89-4350-a76d-7e8e8b293ee8','89024b18-d156-4118-ae3a-997210903102','2c299ef1-4304-4253-9438-f37ab44a795e',0.9491,0.8853,0,'26b62150208725013cd8976e8fd46ffa','2c299ef1__89024b18'),
--   ('e18c50b2-bc45-42ec-9d0a-fdec55906f3a','41cb0689-52b6-4de0-b74c-3bd357dc3e87','89024b18-d156-4118-ae3a-997210903102','2c299ef1-4304-4253-9438-f37ab44a795e',0.9457,0.6872,0,'ea6176e9ff7940b1971f88296eaa3506','2c299ef1__89024b18'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 7: 2e0ee11a__b788bbda   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'Instruction Manual SG100-IS ENG'  (manu='Argus Security' pm='SG100')
--   SUPRIME   2 de 13 chunks de 'Instruction Manual SG100 ENG'  (manu='Argus Security' pm='SG100')
--   PRESERVA  UNIQUE=2, PARTIAL=8, COVERED_NO_TWIN=1
--   cobertura 0.66/0.77 · motivo del representante: empate metadata → más spans únicos (9 vs 2)
--   'SG100-IS' (intrínsecamente seguro) y 'SG100' (estándar) son productos DISTINTOS de Argus.
--   Ground truth de Alberto (s287): las variantes -IS se PRESERVAN aunque el manual sea casi igual.
--   Causa del falso positivo: `documents.product_model` dice 'SG100' en LOS DOS docs; la etiqueta
--   fina vive SOLO a nivel chunk ('SG100-IS' vs 'SG100') → el discriminador de serie no la ve.
--   La etiqueta -IS de chunk queda BLINDADA: ninguna normalización doc→chunks puede borrarla.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 8: 1c6eff80__6d84be7f   [T2-MISMA-MARCA]   *** KEEP-BOTH por Alberto — doc_type DISTINTO, sin marcas ***
--   CONSERVA  'MNDT1070'  (manu='Notifier' pm='LTS-240')
--   SUPRIME   9 de 34 chunks de 'MFDT1070'  (manu='Notifier' pm='LTS-240')
--   PRESERVA  UNIQUE=5, PARTIAL=19, COVERED_NO_TWIN=1
--   cobertura 0.23/0.77 · motivo del representante: empate metadata → más spans únicos (86 vs 21)
--   'MNDT1070' (doc_type='guia_usuario') vs 'MFDT1070' (doc_type='operacion') — mismo
--   producto LTS-240, documentos distintos por FUNCIÓN.
--   VERIFICADO en `documents` (sonda read-only 2026-07-30): el doc_type de los DOS docs ya
--   es correcto y NO es NULL → **no hay fix de doc_type que proponer**.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 9: 681e506b__a7bf5098   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** SUPERSEDED por Alberto — NO es dedup · ver BLOQUE S al final ***
--   CONSERVA  'MI-DT-951_V7.2'  (manu='Notifier' pm='unknown')
--   SUPRIME   2 de 25 chunks de 'Tg-Honeywell_Introduccion'  (manu='Morley' pm='TG-Honeywell')
--   PRESERVA  UNIQUE=12, PARTIAL=10, COVERED_NO_TWIN=1
--   cobertura 0.52/0.75 · motivo del representante: metadata auto-soportada (2/3 vs 1/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'Tg-Honeywell_Introduccion' (más spans únicos (20 vs 10))
--   ⚠ LAS LÍNEAS DE ARRIBA SON LA PROPUESTA DEL CENSUS, con la dirección INVERTIDA
--     respecto a tu adjudicación (el census conservaba la revisión VIEJA). Traza, no acción.
--   'Tg-Honeywell_Introduccion' SUPERSEDE a 'MI-DT-951_V7.2'. VERIFICADO al píxel en el
--   corpus: son el MISMO documento en dos revisiones —
--     MI-DT-951_V7.2         → portada «MI-DT-951 (Rev.:7.2) · Septiembre 2007» · TG-NOTIFIER
--     Tg-Honeywell_Introduccion → portada «MI-DT-951 (Rev.:7.4) · Abril 2009»  · TG-HONEYWELL
--   Las 2 filas del census iban en la dirección CONTRARIA (retiraban chunks de la revisión
--   NUEVA) → SE CAEN. El mecanismo correcto es el linaje del BLOQUE S.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 10: f8020fa4__fc285f22   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'Instruction Manual SG200-IS ENG'  (manu='Argus Security' pm='SG200')
--   SUPRIME   1 de 12 chunks de 'Instruction Manual SG200 ENG'  (manu='Argus Security' pm='SG200')
--   PRESERVA  UNIQUE=1, PARTIAL=9, COVERED_NO_TWIN=1
--   cobertura 0.65/0.74 · motivo del representante: empate metadata → más spans únicos (10 vs 6)
--   'SG200-IS' vs 'SG200' — misma clase que el PAR 7 (variante intrínsecamente segura).
--   Causa: doc-level pm = 'SG200' en ambos; la distinción vive solo en los chunks.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 11: 29c145dc__c270c9c7   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'Instruction Manual SG350-IS ENG'  (manu='Argus Security' pm='SG350')
--   SUPRIME   1 de 8 chunks de 'Instruction Manual SG350 ENG'  (manu='Argus Security' pm='SG350')
--   PRESERVA  PARTIAL=7
--   cobertura 0.66/0.74 · motivo del representante: empate metadata → más spans únicos (10 vs 7)
--   'SG350-IS' vs 'SG350' — misma clase que los PARES 7 y 10.
--   Causa: doc-level pm = 'SG350' en ambos; la distinción vive solo en los chunks.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 12: 65246432__a6d93291   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'I56-4225-001 NRX-OPT Web'  (manu='Notifier' pm='B501RF')
--   SUPRIME   2 de 12 chunks de 'I56-4206-001 NRX Radio Thermals Web'  (manu='Notifier' pm='B501RF')
--   PRESERVA  UNIQUE=2, PARTIAL=6, COVERED_NO_TWIN=2
--   cobertura 0.50/0.72 · motivo del representante: empate metadata → más spans únicos (11 vs 7)
--   'NRX-OPT' (óptico) vs 'NRX Radio Thermals' (térmico NRX-TFIX58) — detectores DISTINTOS.
--   Causa doble: doc-level pm = 'B501RF' en LOS DOS (es la BASE común, no el detector) y el
--   chunk-level del NRX-OPT dice 'EN-54-25', que es la NORMA de enlace radio, no un modelo.
--   Alberto (s287): el pm REAL de 'I56-4225-001 NRX-OPT Web' es **NRX-OPT** → fix al ticket A3.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 13: 153d05f2__9cbcc4fa   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'MIEMI130.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   6 de 46 chunks de 'MIEMI120rev05.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=7, PARTIAL=32, COVERED_NO_TWIN=1
--   cobertura 0.62/0.71 · motivo del representante: empate metadata → más spans únicos (58 vs 44)
--   'MIEMI130' (VSN PLUS, Rev 008) vs 'MIEMI120rev05' (VSN 2-4, Rev 005) — modelos DISTINTOS
--   de la misma familia VSN. Causa: doc-level pm = 'unknown' en LOS DOS; los chunks SÍ los
--   distinguen ('VSN PLUS' vs 'VSN 2-4') → el discriminador de serie no puede disparar.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 14: 1e86c112__4bf442fb   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** APROBADO POR ALBERTO (s287) — VIVO ***
--   CONSERVA  'I56-2081-001ES 6500R(S) Manual'  (manu='System Sensor' pm='6500R')
--   SUPRIME   1 de 20 chunks de 'I56-2081-012 6500R(S)_ES'  (manu='Xtralis' pm='6500R')
--   PRESERVA  UNIQUE=6, PARTIAL=9, COVERED_NO_TWIN=4
--   cobertura 0.68/0.69 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   VEREDICTO Alberto: «mismo producto». Contenido verificado idéntico (Fase 3, ajuste
--   final de ganancia; J=1.000). Decisión 2: la metadata del REPRESENTANTE está BIEN
--   ('System Sensor' / '6500R' en documents Y en sus 22 chunks) → nada que arreglar aquí.
--   NOTA A3 (no bloquea): el doc SUPRIMIDO está atribuido a 'Xtralis' y su texto imprime
--   «System Sensor» 7× y «Xtralis» 0×; su pm de chunk es 'MODELO-6500R' (artefacto).
--   GUARDS RE-PRE-VALIDADOS EN VIVO (read-only, 2026-07-30): md5 sin deriva · no marcado ·
--   canónico existente/no-duplicado/dentro del representante · sin cadenas · gate 3f OK ·
--   0 filas de enunciados colgando.
  ('1475940a-ae7f-4c2d-9f1b-90cfc252ddf5','0498cd0a-0aca-479b-bdbb-c0999cda51ba','1e86c112-02a7-4c91-b64a-4d340601cd6a','4bf442fb-9f63-4205-a2f7-535a5055eac6',1.0,1.0,0,'e62a0ed8d7802f34c76d2b100d9d8190','1e86c112__4bf442fb'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 15: 3caeba69__a6d93291   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'I56-4225-001 NRX-OPT Web'  (manu='Notifier' pm='B501RF')
--   SUPRIME   3 de 16 chunks de 'I56-4205-001 NRX-SMT3 Web'  (manu='Notifier' pm='B501RF')
--   PRESERVA  UNIQUE=3, PARTIAL=8, COVERED_NO_TWIN=2
--   cobertura 0.63/0.69 · motivo del representante: REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'I56-4225-001 NRX-OPT Web' (metadata 3/3, 11 spans únicos). Original por-par: empate metadata → más spans únicos (10 vs 7)
--   'NRX-OPT' (óptico) vs 'NRX-SMT3' (multicriterio) — detectores DISTINTOS.
--   Causa MÁXIMA de este lote: los dos docs son indistinguibles en AMBOS niveles —
--   doc-level pm='B501RF' (la base) y chunk-level pm='EN-54-25' (la norma) en los dos.
--   Los dos valores son artefactos; ninguno nombra el detector → fixes al ticket A3.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 16: 0befac70__af770ec5   [T2-MISMA-MARCA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'MIE-MP-210.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 11 chunks de 'MIE-MI-220.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=5, PARTIAL=4
--   cobertura 0.07/0.69 · motivo del representante: empate metadata → más spans únicos (105 vs 7)
--   ⏸ PREGUNTA ABIERTA de Alberto («analiza y propone») — packet §8.5.
--   VERIFICADO: MIE-MP-210 = manual de la central ZXCE (104 chunks, Vers.1.48 Rev.003, MAYO
--   2002); MIE-MI-220 = «TARJETA DE 20 RELÉS (NC/NO) MOD.REL-2000 · SISTEMA ECO-2000 ·
--   MANUAL DE INSTALACIÓN» (11 chunks). Productos distintos. Los 2 chunks propuestos son
--   «ECUACIONES DE ACTIVACIÓN DE LOS RELÉS» y «EJEMPLOS PRÁCTICOS DE PROGRAMACIÓN»: el
--   lenguaje de expresiones del PANEL, compartido de verdad. MI PROPUESTA: **RECHAZAR** —
--   los chunks del REL-2000 llevan pm='REL-2000' y los del ZXCE pm='ZXCE'; retirarlos deja
--   una consulta de REL-2000 filtrada por modelo sin esos 2 chunks y sin gemelo que la
--   sustituya. Ganancia = 2 chunks; riesgo = pérdida de alcance por modelo.
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('364a687f-a3ca-4379-a8dd-82d5da7c3ba0','3c140682-581e-4542-b7c1-20421d337349','af770ec5-b3b8-4fdd-b8c0-282df17c28ab','0befac70-e041-4f8f-bf13-27678621c334',0.9428,0.7022,0,'4dc6bd51be2f314e9290789f44a0b2c1','0befac70__af770ec5'),
--   ('3fad8a0f-3cf4-42d3-8cb6-8aa9cdab1956','8ff427e4-316b-4695-8b2b-457319e3f3a0','af770ec5-b3b8-4fdd-b8c0-282df17c28ab','0befac70-e041-4f8f-bf13-27678621c334',0.9884,0.847,0,'89d828253c7445008a2343f2899a92fc','0befac70__af770ec5'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 17: f3e9aaa9__fea0ec1d   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'MIE-MI-490.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 7 chunks de 'MIE-MI-480.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=2, PARTIAL=3
--   cobertura 0.62/0.67 · motivo del representante: empate metadata → más spans únicos (6 vs 4)
--   Ground truth de Alberto: MIE-MI-490 = **MMX-10M** y MIE-MI-480 = **MCX-55M** (módulos
--   distintos). Verificado contra la DB: los chunks ya llevan esos pm; el doc-level dice
--   'unknown' en los dos → por eso el census los emparejó. Fix doc-level al ticket A3.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 18: 0ef10ac7__7601da55   [T2-MISMA-MARCA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'MNDT626.pdf'  (manu='Notifier' pm='SMART 3')
--   SUPRIME   4 de 18 chunks de 'MNDT625.pdf'  (manu='Notifier' pm='SMART 3')
--   PRESERVA  UNIQUE=4, PARTIAL=9, COVERED_NO_TWIN=1
--   cobertura 0.49/0.67 · motivo del representante: empate metadata → más spans únicos (24 vs 16)
--   ⏸ PREGUNTA ABIERTA de Alberto (¿mismo modelo, revisiones?) — packet §8.6.
--   NO son revisiones. VERIFICADO en las portadas: MNDT626 = «DETECTORES PARA GAS **TÓXICO**
--   SMART 3 CC-CD (ST/x)» (MN-DT-626_F, 7 OCTUBRE 2009, MTX2081 rev.5); MNDT625 =
--   «DETECTORES PARA GAS **EXPLOSIVO** SMART 3 CC-CD (ST/x)» (MN-DT-625_E, 12 JUNIO 2009).
--   Son las ediciones TÓXICO y EXPLOSIVO del mismo manual: productos distintos (escalas ppm
--   vs %LIE, gases de calibración distintos). MI PROPUESTA: **RECHAZAR** — confundir las dos
--   ediciones en una respuesta es un riesgo de seguridad, no una redundancia.
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('86df92b5-c05c-436c-86c2-27c5bd24a43e','b60fbf81-32c3-4cc1-bb13-dd8341c5781b','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9556,0.8658,0,'6db4573b725d8e47454f5faabf8127dd','0ef10ac7__7601da55'),
--   ('62cd8227-933e-44a5-9bf7-04efe93a27fe','b56ee4b3-b7d9-49e3-813a-1046951e6ddb','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9698,0.6789,0,'9801b799b52fd1e7fda84312619e7d44','0ef10ac7__7601da55'),
--   ('4a98b418-ab93-4bb2-833d-fc78eda133e1','b1ce217d-a3b0-4177-9f0d-73e3fc42f19e','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9444,0.7955,0,'4f4d693c907b6b056caef6346f5d8180','0ef10ac7__7601da55'),
--   ('020ff008-608c-4aff-8103-1f88b4809b21','1524abf5-1ac0-4db1-8674-5b5580bead19','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9658,0.68,0,'29754d329fd93e633aa531997e4f39c4','0ef10ac7__7601da55'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 19: 06887ff1__1d4f6e36   [T2-MISMA-MARCA]   *** ABIERTO — pendiente de tu adjudicación ***
--   CONSERVA  'MNDT516'  (manu='Notifier' pm='PL4')
--   SUPRIME   11 de 26 chunks de 'MNDT516_PL4_ESP-PORT'  (manu='Notifier' pm='PL4')
--   PRESERVA  UNIQUE=9, PARTIAL=5, COVERED_NO_TWIN=1
--   cobertura 0.36/0.67 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   ⏸ PREGUNTA ABIERTA de Alberto (propone: quedarse el ES/EN y retirar el ES/PT) — §8.7.
--   VERIFICADO: los dos son el MISMO manual (pie «MN-DT-516.doc (MT3910.doc) 15/06/2017, 34
--   páginas») en dos ediciones bilingües: MNDT516 = ES/EN, MNDT516_PL4_ESP-PORT = ES/PT.
--   La parte ES es materialmente IDÉNTICA (11 chunks TWIN, 6 de ellos con Jaccard 1.000).
--   Lo 'único' del ES/PT es (a) la traducción PORTUGUESA y (b) prosa de figura distinta —
--   ningún HECHO exclusivo: el único candidato (diagrama de conexión SMART3→PL4+) EXISTE
--   también en el ES/EN. MI PROPUESTA: la propuesta de Alberto es SEGURA en contenido, pero
--   el mecanismo correcto NO es 'superseded' (no hay revisión nueva: misma fecha y doc) sino
--   `status='retired'`, y choca con la política KEEP-BOTH-LANG del propio census (11 pares).
--   Alternativa MÁS BARATA y sin pérdida: aprobar las 11 filas TWIN de abajo (retira solo el
--   ES duplicado y deja el PT servible). Bloque de RETIRO completo, comentado, en §8.7.
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('c2b83c20-6042-4d1f-a2a0-0cc16ba252dc','6c841a90-f3b8-46a6-a12b-d3efb4da8d87','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'74ed428f8048884daf3d14093a12bdf2','06887ff1__1d4f6e36'),
--   ('06d4da66-050d-4f6e-8a76-285da9df0b76','f8b202ef-38f4-483e-9c0e-768145cc16d0','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',0.9686,0.7277,0,'bdbda5f5ead91d8650e5c58141b8d57b','06887ff1__1d4f6e36'),
--   ('eaa2245a-4c6c-4ce8-ad96-6cf37f6a76c4','058fe555-a2f6-4b22-8fa0-93bf94e53557','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'aa7776fa9a0a0e253b55084553fd5deb','06887ff1__1d4f6e36'),
--   ('77359c3b-50b9-4b57-b43c-9b9dddfce424','23b491f5-1bee-4ab0-a91d-50d5e3c3157a','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,0.7149,0,'2af60d1e613fa7c4539e92fe66dbd1f9','06887ff1__1d4f6e36'),
--   ('6e60be5a-7692-45e3-875e-8448a4f8a662','cb030467-436a-44a1-9215-50e51802e863','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'90572524d60ad0b1e97c28b6ef0335a1','06887ff1__1d4f6e36'),
--   ('bb7436f0-0db8-47dc-a1f2-4e4d35aa5cd4','203dced1-79d0-4552-85be-a225e079a85a','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'a5961dc68b2fe3f7d00dae7be4900546','06887ff1__1d4f6e36'),
--   ('211e888f-1791-457a-a8ae-fadb0239929f','8f55077d-f11a-4096-8477-95349a41f7f0','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'f4f4843f993366352a9aa31d60b54e04','06887ff1__1d4f6e36'),
--   ('feac81a2-23a6-42cd-94cb-c2d0750791b8','53a75fec-4236-4ab4-a672-de6752aef8cd','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',1.0,1.0,0,'e74589eb0425ca48a25d5f96f1535240','06887ff1__1d4f6e36'),
--   ('68336fb4-70ba-42e4-91d7-05e064ab1652','63316537-8f75-4fb5-a985-4ac0988ae6ee','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',0.959,0.7164,0,'85f0d119653231c063af88e6cdaf0efb','06887ff1__1d4f6e36'),
--   ('a68f7c17-1580-453b-91b8-b46ccd75ceab','a7b8773a-c1fc-4b46-9af9-4af5b5a06115','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',0.9827,0.8796,0,'0f069ce5fd421da6df80d57958518e3f','06887ff1__1d4f6e36'),
--   ('764e6435-c958-4ad6-ab95-16623974becc','6d8b7b5c-b45b-4075-94ed-edd77212c17c','1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1',0.9808,0.9596,0,'bab49bff35ff9c53e4202f930bcf5948','06887ff1__1d4f6e36'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 20: 496ef3af__f3e9aaa9   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'MIE-MI-490.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 6 chunks de 'MIE-MI-470.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=1, PARTIAL=3
--   cobertura 0.55/0.66 · motivo del representante: REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'MIE-MI-490.pdf' (metadata 2/3, 6 spans únicos). Original por-par: empate metadata → más spans únicos (6 vs 4)
--   Ground truth de Alberto: el 2º doc (MIE-MI-470) es **CMX-10RM**, no una variante del 490.
--   Verificado: chunks 'MMX-10M' (490) vs 'CMX-10RM' (470); doc-level 'unknown' en ambos.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 21: 1e2b058a__4421642f   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'MNDT710_B.pdf'  (manu='Spectrex' pm='20/20U, 20/20UB')
--   SUPRIME   6 de 41 chunks de 'MNDT720.pdf'  (manu='Spectrex' pm='20/20L, 20/20LB')
--   PRESERVA  UNIQUE=14, PARTIAL=21
--   cobertura 0.56/0.66 · motivo del representante: empate metadata → más spans únicos (36 vs 30)
--   Ground truth de Alberto: MNDT710_B = **20/20U / 20/20UB** y MNDT720 = 20/20L / 20/20LB
--   (Spectrex). Aquí la metadata SÍ los distinguía en los dos niveles — el census los
--   emparejó por plantilla común, no por metadata rota. Es la clase KEEP-BOTH-SERIE que el
--   discriminador dejó escapar (los pm son cadenas multi-modelo separadas por coma).
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 22: 5e483105__71654eda   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]   *** SUPERSEDED por Alberto — NO es dedup · ver BLOQUE S al final ***
--   CONSERVA  'MN-DT-951_v7.2'  (manu='Notifier' pm='unknown')
--   SUPRIME   1 de 57 chunks de 'TG-Honeywell_Usuario'  (manu='Morley' pm='TG-Honeywell')
--   PRESERVA  UNIQUE=33, PARTIAL=17, COVERED_NO_TWIN=6
--   cobertura 0.40/0.66 · motivo del representante: metadata auto-soportada (2/3 vs 1/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'TG-Honeywell_Usuario' (más spans únicos (61 vs 24))
--   ⚠ LAS LÍNEAS DE ARRIBA SON LA PROPUESTA DEL CENSUS, con la dirección INVERTIDA
--     respecto a tu adjudicación (el census conservaba la revisión VIEJA). Traza, no acción.
--   'TG-Honeywell_Usuario' SUPERSEDE a 'MN-DT-951_v7.2'. VERIFICADO al píxel:
--     MN-DT-951_v7.2        → portada «MN-DT-951 (Rev.:7.2) · Septiembre 2007» · TG-NOTIFIER
--     TG-Honeywell_Usuario  → portada «MN-DT-951 (Rev.:7.4) · 06/04/2017»    · TG-HONEYWELL
--   La fila del census iba en la dirección CONTRARIA → SE CAE. Ver BLOQUE S.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 23: 29a94dea__30c75a7c   [T2-MISMA-MARCA]   *** RECHAZADO por Alberto — PRODUCTOS DISTINTOS ***
--   CONSERVA  'MIE-MI-431rv2_1.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   1 de 8 chunks de 'MIE-MI-450.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=7
--   cobertura 0.33/0.65 · motivo del representante: empate metadata → más spans únicos (17 vs 7)
--   Ground truth de Alberto: MIE-MI-450 es la **IMPRESORA** de las centrales ZXAE/ZXEE.
--   Verificado al píxel en el corpus: su portada dice «IMPRESORA DE LAZO PERIFÉRICO /
--   MOD.EXP-060R / MANUAL DE INSTALACIÓN»; MIE-MI-431 es el repetidor ZXr-A / ZXr-P.
--   Causa: doc-level pm='unknown' en los dos (los chunks sí dicen EXP-060R / ZXR50A-ZXR50P).
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 24: af5d5d01__b9c694a3   [T2-MISMA-MARCA]   *** KEEP-BOTH por Alberto — doc_type DISTINTO, sin marcas ***
--   CONSERVA  '00-3280-501-4009-05_r005_2x-a_series_installation_manual_es.pdf'  (manu='Aritech' pm='2X-A')
--   SUPRIME   5 de 44 chunks de '00-3280-505-4009-04_r004_2x-a_series_operation_manual_es.pdf'  (manu='Aritech' pm='2X-A')
--   PRESERVA  UNIQUE=16, PARTIAL=16, COVERED_NO_TWIN=7
--   cobertura 0.20/0.62 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   '..._2x-a_series_installation_manual_es' (doc_type='instalacion') vs
--   '..._2x-a_series_operation_manual_es' (doc_type='operacion') — Aritech 2X-A.
--   VERIFICADO en `documents`: los dos doc_type ya son correctos y no son NULL →
--   **no hay fix de doc_type que proponer**.
--   (sin filas en este paste)
-- ────────────────────────────────────────────────────────────────────────────────────────────────
  ('00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',
   '00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',
   0, 0, 0, '', '__SENTINELA__');
-- La fila SENTINELA existe solo para que el INSERT sea sintácticamente válido cuando TODAS
-- las filas reales están comentadas. Se borra aquí; si no aprobaste ningún par, la staging
-- queda vacía y el guard 3 aborta la transacción (nada se aplica).
DELETE FROM _s287_dedup_staging WHERE pair_id = '__SENTINELA__';

-- 2. BACKUP (persistente, para rollback post-COMMIT)
CREATE TABLE IF NOT EXISTS _s287_dedup_backup AS
SELECT c.id, c.duplicate_of, md5(c.content) AS md5_content, now() AS backed_at
FROM chunks_v2 c
WHERE c.id IN (SELECT chunk_id FROM _s287_dedup_staging);

-- 3. GUARDS previos (cualquiera aborta TODO)
DO $$
DECLARE n int; m int;
BEGIN
  SELECT count(*) INTO n FROM _s287_dedup_staging;
  IF n = 0 THEN RAISE EXCEPTION 'staging vacía — nada que aplicar (adjudica y descomenta)'; END IF;

  -- 3a. anti-deriva: el contenido de cada chunk es el que vio el census
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE md5(c.content) <> s.md5_content_before;
  IF m > 0 THEN RAISE EXCEPTION 'DERIVA: % chunks cambiaron de contenido desde el census', m; END IF;

  -- 3b. ninguno estaba ya marcado
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE c.duplicate_of IS NOT NULL;
  IF m > 0 THEN RAISE EXCEPTION '% chunks ya tenían duplicate_of', m; END IF;

  -- 3c. el canónico existe, vive en el doc REPRESENTANTE y NO está marcado (sin cadenas)
  SELECT count(*) INTO m FROM _s287_dedup_staging s
    LEFT JOIN chunks_v2 c ON c.id = s.canonical_chunk_id
   WHERE c.id IS NULL OR c.duplicate_of IS NOT NULL OR c.document_id <> s.doc_representative;
  IF m > 0 THEN RAISE EXCEPTION '% punteros canónicos inválidos (inexistente, ya duplicado, o fuera del representante)', m; END IF;

  -- 3d. el chunk a marcar vive en el doc SUPRIMIDO
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE c.document_id <> s.doc_suppressed;
  IF m > 0 THEN RAISE EXCEPTION '% chunks no pertenecen al doc que se suprime', m; END IF;

  -- 3e. ningún chunk es a la vez marcado y canónico de otro
  SELECT count(*) INTO m FROM _s287_dedup_staging a
    JOIN _s287_dedup_staging b ON a.chunk_id = b.canonical_chunk_id;
  IF m > 0 THEN RAISE EXCEPTION 'cadena de duplicados detectada (% filas)', m; END IF;

  -- 3f. el invariante del gate viaja en los datos y se re-verifica aquí
  SELECT count(*) INTO m FROM _s287_dedup_staging
   WHERE covered_word_frac < 0.92
      OR max_uncovered_span_words >= 25
      OR twin_jaccard < 0.6;
  IF m > 0 THEN RAISE EXCEPTION 'GATE SPAN-DIFF violado en % filas — ABORTA', m; END IF;

  -- 3g. FUGA de satélites: el RPC de enunciados NO filtra por duplicate_of del padre
  --     (migrations/012_enunciados_rpc_filters.sql) → si hubiera filas, marcarlas aquí
  --     dejaría contenido retirado servible por el canal multivector.
  SELECT count(*) INTO m FROM chunks_v2_enunciados e
   WHERE e.parent_id IN (SELECT chunk_id FROM _s287_dedup_staging);
  IF m > 0 THEN RAISE EXCEPTION 'FUGA enunciados: % filas cuelgan de chunks a marcar — trátalas antes', m; END IF;
  -- (hyq NO necesita tratamiento: retriever.py:1095-1098 ya lo guarda client-side)
END $$;

-- 4. UPDATE atómico
WITH upd AS (
  UPDATE chunks_v2 c
     SET duplicate_of = s.canonical_chunk_id
    FROM _s287_dedup_staging s
   WHERE c.id = s.chunk_id
     AND c.duplicate_of IS NULL
     AND md5(c.content) = s.md5_content_before
  RETURNING c.id
)
SELECT count(*) AS updated INTO TEMP tmp_s287_updated FROM upd;

DO $$
DECLARE n int; e int;
BEGIN
  SELECT updated INTO n FROM tmp_s287_updated;
  SELECT count(*) INTO e FROM _s287_dedup_staging;
  IF n <> e THEN RAISE EXCEPTION 'updated % <> staging % — ABORTA TODO', n, e; END IF;
END $$;

SELECT (SELECT count(*) FROM _s287_dedup_staging) AS staged,
       (SELECT updated FROM tmp_s287_updated)     AS updated,
       (SELECT count(*) FROM _s287_dedup_backup)  AS backed_up;

-- ROLLBACK post-COMMIT (dedup):
--   UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of
--     FROM _s287_dedup_backup b WHERE c.id = b.id;
-- ROLLBACK post-COMMIT (metadata-fix del bloque 0):
--   UPDATE documents d SET manufacturer = b.manufacturer, product_model = b.product_model
--     FROM _s287_metafix_backup_documents b WHERE d.id = b.id;
--   UPDATE chunks_v2 c SET manufacturer = b.manufacturer, product_model = b.product_model
--     FROM _s287_metafix_backup_chunks b WHERE c.id = b.id;

COMMIT;   -- <-- para dry-run: ROLLBACK


-- ###########################################################################################
-- #                                                                                          #
-- #   BLOQUE S — LINAJE DE REVISIÓN (clase SUPERSEDED)  ***COMENTADO ENTERO***               #
-- #   PAR 9 y PAR 22 · pendiente de tu OK AL MECANISMO, no solo al veredicto.                #
-- #   TRANSACCIÓN SEPARADA: no forma parte del paste de dedup de arriba.                     #
-- #                                                                                          #
-- ###########################################################################################
--
-- QUÉ ADJUDICASTE (s287) y qué lo confirma en la FUENTE (sonda read-only 2026-07-30):
--
--   PAR 9   MI-DT-951 «Manual de introducción»
--           VIEJO  681e506b  'MI-DT-951_V7.2'            portada: MI-DT-951 (Rev.:7.2) · Septiembre 2007 · TG-NOTIFIER
--           NUEVO  a7bf5098  'Tg-Honeywell_Introduccion' portada: MI-DT-951 (Rev.:7.4) · Abril 2009      · TG-HONEYWELL
--
--   PAR 22  MN-DT-951 «Manual de usuario»
--           VIEJO  5e483105  'MN-DT-951_v7.2'            portada: MN-DT-951 (Rev.:7.2) · Septiembre 2007 · TG-NOTIFIER
--           NUEVO  71654eda  'TG-Honeywell_Usuario'      portada: MN-DT-951 (Rev.:7.4) · 06/04/2017      · TG-HONEYWELL
--
--   Mismo número de documento, revisión mayor, y el cambio de marca Notifier→Honeywell que
--   explica por qué el census los vio como "cross-brand". Es EXACTAMENTE la clase que el gap
--   #9 del packet declaró que `duplicate_of` NO arregla. Tu adjudicación es la correcta.
--
--   CONTEXTO DE FAMILIA (encontrado de paso, read-only): la familia TG-DT-951 tiene TRES
--   generaciones en el corpus, no dos —
--     · MIDT951_v5-87 (06c08203) «MI-DT-951 (Rev:5.87) · Mayo 2005»  → 31 chunks
--     · MNDT951_v5-87 (81534fd9) «MN-DT-951 (Rev:5.87) · Mayo 2005»  → 61 chunks
--     · MP-DT-951_v7.2 (067598cb) «MP-DT-951 (Rev.:7.2) · Sept 2007» → 89 chunks (manual de
--       configuración; no tiene pareja 7.4 entre los 24 pares)
--   Los 4 docs del BLOQUE S tienen HOY `status='active'`, `supersedes_id IS NULL` y
--   `superseded_by_id IS NULL` (verificado). El linaje del corpus está SIN POBLAR.
--
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- LO QUE ENCONTRÉ Y CAMBIA LA DECISIÓN (léelo antes de elegir variante)
-- ═══════════════════════════════════════════════════════════════════════════════════════════
--
-- (1) `status='superseded'` NO es "marcar una etiqueta": APAGA EL DOC ENTERO en runtime.
--     `retrieve_chunks` descarta todo chunk cuyo documento padre no esté 'active'
--     (src/rag/retriever.py:1789-1794 y :2802). Coste medido de apagar los dos viejos:
--       · PAR 9  → 16 chunks activos dejan de servirse. El census midió que solo el
--                  **75.4%** de las palabras del viejo están en el nuevo (clases del viejo:
--                  UNIQUE 5 · PARTIAL 6 · TWIN 4 · COVERED_NO_TWIN 1).
--       · PAR 22 → 38 chunks activos dejan de servirse, y solo el **66.0%** de sus palabras
--                  están en el nuevo (UNIQUE 14 · PARTIAL 16 · COVERED_NO_TWIN 8 · TWIN 0).
--     Es decir: la revisión 7.4 NO contiene todo lo que decía la 7.2. Apagarlas retira
--     contenido servible que ninguna otra fuente cubre.
--
-- (2) HAY HUÉRFANOS (el patrón HP011, ya visto en este repo). Otros chunks apuntan con
--     `duplicate_of` a chunks de los docs VIEJOS. Si el viejo se apaga, esos chunks siguen
--     suprimidos y su canónico deja de servirse → el contenido desaparece por completo:
--       · PAR 9  → 2 punteros entrantes, los dos desde MIDT951_v5-87 (06c08203).
--       · PAR 22 → 13 punteros entrantes: **10 desde el propio doc NUEVO** (71654eda),
--                  2 desde MNDT951_v5-87 (81534fd9) y 1 interno.
--     Los 10 del doc NUEVO son literalmente el defecto que la migración
--     `supabase/migrations/20260721190847_reconcile_hp011_v04_v07_lifecycle.sql` tuvo que
--     reparar en HP011 («38 v.07 chunks currently point at v.04 through duplicate_of […]
--     those links make parts of the authoritative revision unservable»). Cualquier variante
--     que apague el viejo DEBE des-enlazarlos, o deja 10 trozos de la revisión AUTORITATIVA
--     sin servir.
--
-- (3) Las filas que el census proponía para estos 2 pares iban en la DIRECCIÓN CONTRARIA
--     (retiraban chunks del doc NUEVO). Están fuera del paste de arriba. Bien cazado.
--
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- TRES VARIANTES. MI RECOMENDACIÓN: **A ahora**, y B solo si decides que la 7.2 no debe
-- servirse aunque tenga contenido propio. C es el punto medio si quieres además limpiar el
-- solape del PAR 9 sin perder nada.
-- ═══════════════════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────────────────
-- VARIANTE A (RECOMENDADA) — LINAJE SIN APAGAR NADA
--   Materializa la relación (`supersedes_id` / `superseded_by_id`) y deja `status='active'`.
--   Efecto en runtime: **CERO** — el filtro de lifecycle solo mira `status`; `supersedes_id`
--   y `superseded_by_id` no los lee ningún path de retrieval (verificado: solo aparecen en
--   migraciones y en el contrato de DOCUMENT_MANAGEMENT).
--   Por qué es la correcta primero: registra tu ground-truth de forma duradera y reversible,
--   no pierde ni un chunk, no crea huérfanos, y deja la política de "servir solo la última
--   revisión" para cuando se decida CON la medida delante (probe de pool + sweep-39).
--   Es el mismo orden que siguió el repo en s64/DEC-045: primero poblar el linaje, después
--   consumirlo.
--
-- BEGIN;
-- SET LOCAL lock_timeout = '5s';
-- SET LOCAL statement_timeout = '30s';
--
-- CREATE TABLE IF NOT EXISTS _s287_lineage_backup_documents AS
-- SELECT id, status, supersedes_id, superseded_by_id, revision, revision_date, now() AS backed_at
--   FROM documents
--  WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
--               '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e');
--
-- DO $$
-- DECLARE m int;
-- BEGIN
--   -- pre-estado EXACTO de los 4 docs (si alguno ya tiene linaje, ABORTA)
--   SELECT count(*) INTO m FROM documents
--    WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
--                 '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e')
--      AND status = 'active' AND supersedes_id IS NULL AND superseded_by_id IS NULL;
--   IF m <> 4 THEN RAISE EXCEPTION 'linaje: los 4 docs no están en el pre-estado (% de 4) — ABORTA', m; END IF;
--   -- cardinalidad de chunks (ancla anti-deriva)
--   SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '681e506b-daaa-4f78-8336-aa732695962c';
--   IF m <> 24 THEN RAISE EXCEPTION 'MI-DT-951_V7.2 tiene % chunks, la sonda vio 24 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = 'a7bf5098-6187-4df9-863b-b24d62d0687e';
--   IF m <> 26 THEN RAISE EXCEPTION 'Tg-Honeywell_Introduccion tiene % chunks, la sonda vio 26 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '5e483105-7539-45be-9858-d50ecbdc5cd0';
--   IF m <> 54 THEN RAISE EXCEPTION 'MN-DT-951_v7.2 tiene % chunks, la sonda vio 54 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '71654eda-7c94-4aec-9ce3-4310fb254e7e';
--   IF m <> 105 THEN RAISE EXCEPTION 'TG-Honeywell_Usuario tiene % chunks, la sonda vio 105 — ABORTA', m; END IF;
-- END $$;
--
-- -- PAR 9: 7.4 (nuevo) supersede a 7.2 (viejo)
-- UPDATE documents SET supersedes_id = '681e506b-daaa-4f78-8336-aa732695962c'
--  WHERE id = 'a7bf5098-6187-4df9-863b-b24d62d0687e' AND supersedes_id IS NULL;
-- UPDATE documents SET superseded_by_id = 'a7bf5098-6187-4df9-863b-b24d62d0687e'
--  WHERE id = '681e506b-daaa-4f78-8336-aa732695962c' AND superseded_by_id IS NULL;
-- -- PAR 22
-- UPDATE documents SET supersedes_id = '5e483105-7539-45be-9858-d50ecbdc5cd0'
--  WHERE id = '71654eda-7c94-4aec-9ce3-4310fb254e7e' AND supersedes_id IS NULL;
-- UPDATE documents SET superseded_by_id = '71654eda-7c94-4aec-9ce3-4310fb254e7e'
--  WHERE id = '5e483105-7539-45be-9858-d50ecbdc5cd0' AND superseded_by_id IS NULL;
--
-- -- OPCIONAL dentro de A (recomendado: la portada da el dato y hoy está NULL en los 4):
-- -- UPDATE documents SET revision = '7.2', revision_date = DATE '2007-09-01'
-- --  WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0');
-- -- UPDATE documents SET revision = '7.4', revision_date = DATE '2009-04-01'
-- --  WHERE id = 'a7bf5098-6187-4df9-863b-b24d62d0687e';
-- -- UPDATE documents SET revision = '7.4', revision_date = DATE '2017-04-06'
-- --  WHERE id = '71654eda-7c94-4aec-9ce3-4310fb254e7e';
--
-- DO $$
-- DECLARE m int;
-- BEGIN
--   SELECT count(*) INTO m FROM documents d JOIN documents n ON n.id = d.superseded_by_id
--    WHERE d.id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--      AND n.supersedes_id = d.id AND d.status = 'active' AND n.status = 'active';
--   IF m <> 2 THEN RAISE EXCEPTION 'linaje incompleto (% de 2 cadenas) — ABORTA', m; END IF;
-- END $$;
-- SELECT id, source_pdf_filename, status, supersedes_id, superseded_by_id FROM documents
--  WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
--               '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e');
-- COMMIT;   -- dry-run: ROLLBACK
--
-- ROLLBACK post-COMMIT de A:
--   UPDATE documents d SET status = b.status, supersedes_id = b.supersedes_id,
--          superseded_by_id = b.superseded_by_id, revision = b.revision, revision_date = b.revision_date
--     FROM _s287_lineage_backup_documents b WHERE d.id = b.id;

-- ───────────────────────────────────────────────────────────────────────────────────────────
-- VARIANTE B — LIFECYCLE COMPLETO (apaga las revisiones 7.2) · SOLO si aceptas el coste
--   Añade a A: `status='superseded'` en los dos viejos + la REPARACIÓN DE HUÉRFANOS.
--   COSTE DECLARADO (medido arriba): 16 + 38 = **54 chunks activos dejan de servirse**, de los
--   cuales el census marca 19 UNIQUE y 22 PARTIAL — contenido que la 7.4 NO tiene.
--   NO lo recomiendo sin medir antes (probe de pool + sweep-39). Si aun así lo quieres, la
--   reparación de huérfanos NO es opcional.
--
-- BEGIN;
-- SET LOCAL lock_timeout = '5s';
-- SET LOCAL statement_timeout = '30s';
-- -- (ejecuta ANTES el bloque de guards + backup de la VARIANTE A, sin su COMMIT)
--
-- CREATE TABLE IF NOT EXISTS _s287_lineage_backup_orphans AS
-- SELECT id, document_id, duplicate_of, now() AS backed_at FROM chunks_v2
--  WHERE id IN ('3095f0b9-7e44-4832-a104-f2b00e6064ed','3d2a6a21-fe1f-4240-9635-ad9ccd953ffe',
--               '91fae1ce-4642-4355-9f22-d0035b254682','efddc1d4-2dd2-43f4-a0f2-56cf4028359b',
--               '561fc173-29c4-42c1-a888-7b07ce921912','02bab8bb-3b05-438a-b5e0-d11cf0b10217',
--               '509c2245-2d2a-47ad-bc45-b23c5be7571c','7bcf5bcf-31ef-488b-a524-205c15cbe97b',
--               'fa221fa4-fc77-41bf-99d4-acda355cb012','b97709fe-8917-40e7-b99a-4d3c24e15f34',
--               '16ad0101-ca46-4f26-ae36-e84fca7049d6','8d1a19c8-5180-4d43-aee7-a0d76261a349',
--               '7e65dd25-014a-4785-a6fc-83cbbeed1d9c','963a45ef-d423-4048-a691-8c2eab3bee6f');
--
-- DO $$
-- DECLARE m int;
-- BEGIN
--   -- la topología de huérfanos es EXACTAMENTE la que vio la sonda (2 + 13, con 1 interno)
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    WHERE t.document_id = '681e506b-daaa-4f78-8336-aa732695962c' AND c.document_id <> t.document_id;
--   IF m <> 2 THEN RAISE EXCEPTION 'PAR 9: % punteros entrantes, la sonda vio 2 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    WHERE t.document_id = '5e483105-7539-45be-9858-d50ecbdc5cd0' AND c.document_id <> t.document_id;
--   IF m <> 12 THEN RAISE EXCEPTION 'PAR 22: % punteros entrantes externos, la sonda vio 12 — ABORTA', m; END IF;
-- END $$;
--
-- UPDATE documents SET status = 'superseded'
--  WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--    AND status = 'active';
--
-- -- REPARACIÓN DE HUÉRFANOS (patrón HP011): todo chunk de un doc que SIGUE activo y que
-- -- apuntaba a un chunk del doc apagado se des-enlaza para volver a servirse.
-- UPDATE chunks_v2 c SET duplicate_of = NULL
--   FROM chunks_v2 t
--  WHERE t.id = c.duplicate_of
--    AND t.document_id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--    AND c.document_id NOT IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0');
--
-- DO $$
-- DECLARE m int;
-- BEGIN
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    JOIN documents d ON d.id = t.document_id
--   WHERE d.status <> 'active' AND c.document_id <> t.document_id;
--   IF m > 0 THEN RAISE EXCEPTION 'quedan % huérfanos apuntando a docs no-activos — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM documents
--    WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--      AND status = 'superseded' AND superseded_by_id IS NOT NULL;
--   IF m <> 2 THEN RAISE EXCEPTION 'lifecycle incompleto (% de 2) — ABORTA', m; END IF;
-- END $$;
-- COMMIT;   -- dry-run: ROLLBACK
--
-- ROLLBACK post-COMMIT de B: el de A +
--   UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of
--     FROM _s287_lineage_backup_orphans b WHERE c.id = b.id;

-- ───────────────────────────────────────────────────────────────────────────────────────────
-- VARIANTE C — A + dedup POR CHUNK de lo que la 7.4 SÍ contiene (sin apagar nada)
--   Retira solo los chunks del viejo que pasan el gate span-diff contra el nuevo. Medido:
--     · PAR 9  → 4 chunks TWIN (los 4 con guards re-pre-validados en vivo, filas abajo).
--     · PAR 22 → **0 chunks**: el doc viejo no tiene ni un TWIN contra el nuevo (el manual de
--                usuario se reescribió entre 2007 y 2017) → en el PAR 22 no hay nada que dedup
--                pueda hacer. Eso mismo es la prueba de que `duplicate_of` no es el mecanismo.
--   Es el complemento honesto de A: concentra la cita en la revisión nueva donde el contenido
--   es demostrablemente el mismo, y deja servible todo lo demás de la 7.2.
--   Para usarlo: pega estas 4 filas en el VALUES del paste de arriba (staged pasaría a 16).
--
--   ('20d02359-0f14-46bf-a627-555ef9e87dd5','d5ddafd4-63dd-4224-9352-0cae9da6bc0d','681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',0.9858,0.7992,0,'9bf547237b992e5cd4877df3f59132eb','681e506b__a7bf5098'),   -- idx3 p5 424w
--   ('1d39689b-c7f8-4e9d-a250-de6ef3e51371','ca200e02-ec5e-404b-beaf-d69e7acd23d8','681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',0.9882,0.808,0,'ddadb44a2a0141bd11b454a66a42b8d8','681e506b__a7bf5098'),   -- idx13 p21 423w
--   ('25faa43c-c7cf-44de-b64a-a98cbc6797e6','9fd06c80-a360-41e5-92ac-088caf9828a9','681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',1.0,0.6783,0,'16cabf5e7d474e3408434e1c6c76795a','681e506b__a7bf5098'),   -- idx14 p22 104w
--   ('fe53736d-c51e-4567-a2f5-3bb2e0d55097','4dcf2f0a-e87b-466d-9cd1-e86764570b3a','681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',0.9833,0.917,0,'9e7232fac8af40f77febf722be1dee55','681e506b__a7bf5098'),   -- idx21 p32 239w
--
--   OJO en C: el chunk 1d39689b del viejo es HOY el canónico de ca200e02 (del doc nuevo) —
--   la relación está INVERTIDA en la DB. Marcarlo sin más crearía cadena y el guard 3e
--   abortaría. Antes hay que des-enlazar ca200e02 (mismo des-enlace HP011 de la variante B,
--   acotado a ese chunk). Está declarado aquí para que no sea una sorpresa en el paste.

-- ───────────────────────────────────────────────────────────────────────────────────────────
-- GAPS DECLARADOS DEL BLOQUE S (los tres, de entrada)
--  1. Ninguna variante está MEDIDA en pool/eval. A tiene efecto-cero por construcción, así que
--     no necesita gate; B y C sí lo necesitan (probe de composición + sweep-39 de no-regresión).
--  2. El linaje de la familia queda a MEDIAS: las generaciones v5.87 (MIDT951/MNDT951) y el
--     MP-DT-951_v7.2 siguen sin cadena. Poblarlos es el mismo patrón, pero NO están adjudicados
--     por ti → no los toco. Van al ticket A3.
--  3. `document_family` de los 4 docs es el filename (MI-DT-951_V7.2, Tg-Honeywell_Introduccion…),
--     así que la familia NO agrupa las revisiones. El linaje por FK funciona igual, pero
--     cualquier consumo futuro por `document_family` no verá la relación. Es el defecto
--     filename-naive ya conocido (DECISIONS.md:909) — no lo arreglo aquí.
