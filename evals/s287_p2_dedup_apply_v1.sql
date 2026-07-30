-- s287 P2 — dedup a nivel DOCUMENTO: marca `duplicate_of` de los chunks GEMELOS
-- del doc no-representante. GENERADO read-only por scripts/s287_p2_dedup_census.py.
-- Spec: evals/s287_etapa2_design_brief_v1.md (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF Sol-6).
-- Census: evals/s287_p2_dedup_census_v1.json
-- Packet: evals/s287_p2_dedup_adjudicacion_packet_v1.md  ← LÉELO ANTES DE APROBAR NADA
--
-- ###########################################################################################
-- #  TODAS las filas salen COMENTADAS, A PROPÓSITO. Ningún par entra vivo.                  #
-- #  El census midió que CADA clase de candidato arrastra un riesgo de IDENTIDAD que solo   #
-- #  la adjudicación resuelve (variantes -IS, manual-vs-datasheet, módulos hermanos con     #
-- #  pm='unknown', rebadges OEM Notifier/Morley). APROBAR UN PAR = quitar el '-- ' inicial  #
-- #  de las filas de su bloque. No hay que tocar comas: la fila SENTINELA cierra el VALUES. #
-- ###########################################################################################
--
-- INVARIANTE del gate SPAN-DIFF (re-verificado en SQL, guard 3f): solo se marcan chunks de
-- clase TWIN — >= 0.92 de sus palabras cubiertas por el doc representante,
-- NINGUNA racha no cubierta de >= 25 palabras, y gemelo con
-- Jaccard >= 0.6. Los chunks UNIQUE / PARTIAL / COVERED_NO_TWIN / SHORT NO se
-- tocan: siguen sirviéndose desde el doc "suprimido" (la supresión es POR CHUNK, no por doc).
--
-- Propuestas: 120 marcas en 24 pares · tiers {'T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA': 6, 'T1-DOC-IDENTICO': 1, 'T2-MISMA-MARCA': 17}
-- Dry-run: cambia COMMIT por ROLLBACK.

BEGIN;

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
--   CONSERVA  'IS5001-F_IS-mA1_EN'  (manu='European Safety Systems' pm='IS5001')
--   SUPRIME   9 de 18 chunks de 'manual IS MA1'  (manu='Detnov' pm='unknown')
--   PRESERVA  UNIQUE=4, PARTIAL=5
--   cobertura 0.72/0.89 · motivo del representante: metadata auto-soportada (2/3 vs 0/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'manual IS MA1' (más spans únicos (13 vs 7))
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('25d7fd21-e168-43e4-b2e6-b73b15aff49d','d4ae732f-2838-4134-a558-680b1ac36bb8','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9653,0.7444,0,'536b6baa12e5a359a8eab165f317ea59','2b694083__a6b9dc84'),
--   ('68c40b6f-c4a4-478e-adff-bf32febc2cd7','1a7ac511-31fd-4281-a482-157c3dabcb15','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9897,0.7157,0,'c644615d4ff1f01a55d666970f7b2f80','2b694083__a6b9dc84'),
--   ('b21ff3e2-56f0-4d12-96d9-6735f6648a7c','2b9a9f41-f468-42db-895b-920fb5050472','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9766,0.8022,0,'f68497bc353ec2fe9436b707b6e805ac','2b694083__a6b9dc84'),
--   ('1ffd36f5-2f6d-4759-aac5-e1cf532833da','9d4ae236-ad66-428e-91b2-5fd254715b23','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',1.0,1.0,0,'60db8eb69268cf462eba150b808b0270','2b694083__a6b9dc84'),
--   ('e3a101aa-41dd-4aa1-a042-1b7b01bcf467','c07ed164-df92-4e07-9e8a-d1a4d730d3f0','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',1.0,1.0,0,'7276f8f9892f36fe059b6cef63171caf','2b694083__a6b9dc84'),
--   ('70f4ac0e-1497-460a-b893-4bcfd33f0168','d4e91d5f-2721-45bb-8cbb-ca7fbbdd9fc9','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9545,0.8261,0,'29f141cd25f722349ca696c08a3ae242','2b694083__a6b9dc84'),
--   ('ba38fed9-e1a9-4388-941e-78de2289e27a','4feea9a8-59d3-4742-9ab9-2ff9aee1caa0','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9728,0.7052,0,'57cf13b3eedf4bd9fc13c246927a78df','2b694083__a6b9dc84'),
--   ('df475873-b2d4-4884-9086-a527771a3f82','e10519a0-e237-49df-a151-83a859609a8e','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',0.9921,0.6642,0,'0ceddf025b3558e46a189d23b48a9b1d','2b694083__a6b9dc84'),
--   ('d335a010-5715-4214-975b-1e18bf58ac75','7eff6257-85e6-402d-9947-90c7336ff7e1','a6b9dc84-af6d-4957-a403-4b4c2136557b','2b694083-5b21-4f1a-a29b-565072860fb8',1.0,1.0,0,'9bd4ac05997d1e1de79119df222776f2','2b694083__a6b9dc84'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 2: 5e878ee7__eb749df8   [T1-DOC-IDENTICO]
--   CONSERVA  'DXc_Connexion Averia-de-resistencia-de-baterias.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   1 de 1 chunks de 'Averia-de-resistencia-de-baterias-en-central-DXc.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  (nada más en el doc suprimido)
--   cobertura 0.95/0.96 · motivo del representante: empate → más reciente (revision_date/revision/ingested_at)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('f58ad5cd-5d6a-438f-b546-4ff11d5b8b48','c9952764-8b68-4aea-b7ca-9d6a85fa917c','eb749df8-87db-4800-90dd-7d65889822fa','5e878ee7-53eb-4b03-bda3-5fd5de306bba',0.9536,0.7803,0,'fa4905b168fc4c5225f9c099ef755a99','5e878ee7__eb749df8'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 3: 517b87ce__de8c0345   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]
--   CONSERVA  'FS2-1'  (manu='Notifier' pm='FS2-1')
--   SUPRIME   12 de 27 chunks de 'ms1-2-4.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=4, PARTIAL=5, COVERED_NO_TWIN=6
--   cobertura 0.80/0.86 · motivo del representante: metadata auto-soportada (2/3 vs 0/3)
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
-- PAR 4: 7f9ea4ab__acafc5d1   [T2-MISMA-MARCA]
--   CONSERVA  'MNDT1026'  (manu='Notifier' pm='VIEW')
--   SUPRIME   5 de 23 chunks de 'MNDT1025'  (manu='Notifier' pm='VIEW')
--   PRESERVA  UNIQUE=3, PARTIAL=12, COVERED_NO_TWIN=3
--   cobertura 0.64/0.85 · motivo del representante: empate metadata → más spans únicos (18 vs 8)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('130b656a-2ad3-4025-b2bd-7768f46bfacf','a4bcff6e-b2e8-4328-b677-0048da277226','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9915,0.8413,0,'3a92eced40884313b187a82a35431c84','7f9ea4ab__acafc5d1'),
--   ('6def4121-4b61-4737-aba0-e2e488dce100','3d792de5-1b05-4028-b2c2-a2942f9267f6','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9912,0.8522,0,'80d7733541322e0105f98c7de9c290eb','7f9ea4ab__acafc5d1'),
--   ('effaf7c3-413d-4b94-a0d4-7acfde4395fb','6d29d2d8-d34b-4599-a7ca-c118d54a12d7','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9764,0.8617,0,'d4516629a79407f1f286e7df176afb51','7f9ea4ab__acafc5d1'),
--   ('ac8027dc-9c00-4ca5-a89d-7563ab84573f','ae1a68ce-3b87-4699-bd20-4bf3713ea238','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9523,0.6755,0,'cf4cfd643f4405a32a674af1526b9ff3','7f9ea4ab__acafc5d1'),
--   ('685ab164-fac2-41be-ab86-febe0ff66059','d245c6fb-aa4c-40bb-b6b5-1fce2137d302','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.952,0.7912,0,'a0a0cc249800e60cafa252169e33106e','7f9ea4ab__acafc5d1'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 5: 5800c4c0__cbc9c21c   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]
--   CONSERVA  'FS8'  (manu='Notifier' pm='EFS/EM 8')
--   SUPRIME   30 de 63 chunks de 'MS8.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=8, PARTIAL=20, COVERED_NO_TWIN=5
--   cobertura 0.84/0.85 · motivo del representante: metadata auto-soportada (1/3 vs 0/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'MS8.pdf' (más spans únicos (36 vs 27))
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
-- PAR 6: 2c299ef1__89024b18   [T2-MISMA-MARCA]
--   CONSERVA  'D 1148-1 BRS Notifier'  (manu='Notifier' pm='B501AP')
--   SUPRIME   2 de 7 chunks de 'D 1147-1 BRH Notifier'  (manu='Notifier' pm='B501AP')
--   PRESERVA  UNIQUE=2, PARTIAL=2, COVERED_NO_TWIN=1
--   cobertura 0.80/0.83 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('f0154a63-652c-4748-a9fb-a082a4e4b160','1416c36a-2d89-4350-a76d-7e8e8b293ee8','89024b18-d156-4118-ae3a-997210903102','2c299ef1-4304-4253-9438-f37ab44a795e',0.9491,0.8853,0,'26b62150208725013cd8976e8fd46ffa','2c299ef1__89024b18'),
--   ('e18c50b2-bc45-42ec-9d0a-fdec55906f3a','41cb0689-52b6-4de0-b74c-3bd357dc3e87','89024b18-d156-4118-ae3a-997210903102','2c299ef1-4304-4253-9438-f37ab44a795e',0.9457,0.6872,0,'ea6176e9ff7940b1971f88296eaa3506','2c299ef1__89024b18'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 7: 2e0ee11a__b788bbda   [T2-MISMA-MARCA]
--   CONSERVA  'Instruction Manual SG100-IS ENG'  (manu='Argus Security' pm='SG100')
--   SUPRIME   2 de 13 chunks de 'Instruction Manual SG100 ENG'  (manu='Argus Security' pm='SG100')
--   PRESERVA  UNIQUE=2, PARTIAL=8, COVERED_NO_TWIN=1
--   cobertura 0.66/0.77 · motivo del representante: empate metadata → más spans únicos (9 vs 2)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('8d6c561a-c7df-4ea4-b0c3-fefa647ff3fc','c5f71f68-5a5f-4740-8a7e-61f5531904a2','2e0ee11a-e42e-4c25-a5d6-d77924cbdb11','b788bbda-6045-46f5-b645-b54a23bdae5c',1.0,1.0,0,'67664b78ce4dea11fd06bf28218c0038','2e0ee11a__b788bbda'),
--   ('2412344f-367d-4e44-b783-271d1c47897a','411ca95e-bfa5-4e8e-b2d8-0674affe19ad','2e0ee11a-e42e-4c25-a5d6-d77924cbdb11','b788bbda-6045-46f5-b645-b54a23bdae5c',1.0,0.9714,0,'3ba3de2605d602dca630ca7f36827615','2e0ee11a__b788bbda'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 8: 1c6eff80__6d84be7f   [T2-MISMA-MARCA]
--   CONSERVA  'MNDT1070'  (manu='Notifier' pm='LTS-240')
--   SUPRIME   9 de 34 chunks de 'MFDT1070'  (manu='Notifier' pm='LTS-240')
--   PRESERVA  UNIQUE=5, PARTIAL=19, COVERED_NO_TWIN=1
--   cobertura 0.23/0.77 · motivo del representante: empate metadata → más spans únicos (86 vs 21)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('3d614ca6-1106-4566-b1af-73c9f6c7860c','6710fe0b-58da-4b7b-8b60-b1b5a0c97182','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.9675,0.9268,0,'3e9454d55b095253e1d679fbc85d7262','1c6eff80__6d84be7f'),
--   ('56a0391d-f2a4-402f-b193-a911e941464d','aed13542-4f86-4831-abc1-f37e89ce2594','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.9508,0.7037,0,'6fc347fc4f868179a8065ac1e713bb02','1c6eff80__6d84be7f'),
--   ('ed1fdaf4-1994-4664-b0aa-cffc91642a4c','12c55257-4f2d-4d98-b61b-608ef3d0f804','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.943,0.8812,0,'fa3949fd03998fbfc434a39797a8415f','1c6eff80__6d84be7f'),
--   ('13aee284-9aea-4bf2-87f8-7cbafad18be4','0af81402-1c4e-4a6e-b436-1da5353a45fe','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.995,0.8306,0,'b6559d487668697038da6de8a5932263','1c6eff80__6d84be7f'),
--   ('973d572b-d30d-4022-8dc1-0ae8e9c128ad','4ac88edd-ec41-4714-859f-27f94ac5b83b','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.951,0.8341,0,'4004e09882b627356360e8b158258932','1c6eff80__6d84be7f'),
--   ('abc645a3-9bdc-449b-85f2-f70dc1d4d8f0','4877065e-0ec9-42dc-86dc-22f429e3d35a','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.9826,0.7604,0,'ccd1f881889e8510981b9126507c7582','1c6eff80__6d84be7f'),
--   ('f852c200-4ec7-422a-9ecf-b4bf94409ef2','c89118bf-ed8f-4379-9097-aa9fede41f53','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.9558,0.9203,0,'4811d93ad654c388582c08aca2dc4de6','1c6eff80__6d84be7f'),
--   ('85a5bd78-bfab-4930-9df1-7724c8c013f8','b30c1824-e119-45d7-8edc-d43633fa3cb6','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',1.0,1.0,0,'036e5cf59aac9fd46cd518693feda1e5','1c6eff80__6d84be7f'),
--   ('3414db46-1988-44fd-9c63-4cedf9d1b323','0c31110e-9906-4b72-87fa-6841324bac06','1c6eff80-d065-4074-a229-55c8ed391b3e','6d84be7f-0ada-4647-9852-6089d690f8fc',0.9923,0.9839,0,'e5862452eb2bcb281818c0f5c65f04c8','1c6eff80__6d84be7f'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 9: 681e506b__a7bf5098   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]
--   CONSERVA  'MI-DT-951_V7.2'  (manu='Notifier' pm='unknown')
--   SUPRIME   2 de 25 chunks de 'Tg-Honeywell_Introduccion'  (manu='Morley' pm='TG-Honeywell')
--   PRESERVA  UNIQUE=12, PARTIAL=10, COVERED_NO_TWIN=1
--   cobertura 0.52/0.75 · motivo del representante: metadata auto-soportada (2/3 vs 1/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'Tg-Honeywell_Introduccion' (más spans únicos (20 vs 10))
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('ca200e02-ec5e-404b-beaf-d69e7acd23d8','1d39689b-c7f8-4e9d-a250-de6ef3e51371','a7bf5098-6187-4df9-863b-b24d62d0687e','681e506b-daaa-4f78-8336-aa732695962c',0.9353,0.808,0,'52d8774e7b51252007b5e374fca2b847','681e506b__a7bf5098'),
--   ('4dcf2f0a-e87b-466d-9cd1-e86764570b3a','fe53736d-c51e-4567-a2f5-3bb2e0d55097','a7bf5098-6187-4df9-863b-b24d62d0687e','681e506b-daaa-4f78-8336-aa732695962c',0.9916,0.917,0,'8b141c494cc1577939e73338b157d019','681e506b__a7bf5098'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 10: f8020fa4__fc285f22   [T2-MISMA-MARCA]
--   CONSERVA  'Instruction Manual SG200-IS ENG'  (manu='Argus Security' pm='SG200')
--   SUPRIME   1 de 12 chunks de 'Instruction Manual SG200 ENG'  (manu='Argus Security' pm='SG200')
--   PRESERVA  UNIQUE=1, PARTIAL=9, COVERED_NO_TWIN=1
--   cobertura 0.65/0.74 · motivo del representante: empate metadata → más spans únicos (10 vs 6)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('0d7a3e70-cdea-4c04-8978-79b3acff28fd','271a85f7-c29b-46fc-9b63-252233fe4787','fc285f22-cfa5-4c88-b12d-aa18a764a2a7','f8020fa4-cd11-48e5-b80c-39d606dacc8b',1.0,0.9714,0,'f5666060891645a57a46c68ccd14ee6f','f8020fa4__fc285f22'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 11: 29c145dc__c270c9c7   [T2-MISMA-MARCA]
--   CONSERVA  'Instruction Manual SG350-IS ENG'  (manu='Argus Security' pm='SG350')
--   SUPRIME   1 de 8 chunks de 'Instruction Manual SG350 ENG'  (manu='Argus Security' pm='SG350')
--   PRESERVA  PARTIAL=7
--   cobertura 0.66/0.74 · motivo del representante: empate metadata → más spans únicos (10 vs 7)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('5311b986-43c3-4245-819e-f1c51af5dc1b','b8de452b-3d0f-442a-8e2e-fb9be14ea692','29c145dc-f036-4e24-b16f-66ba61f480b6','c270c9c7-80f1-41a9-8639-0b1a624765b5',1.0,1.0,0,'67664b78ce4dea11fd06bf28218c0038','29c145dc__c270c9c7'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 12: 65246432__a6d93291   [T2-MISMA-MARCA]
--   CONSERVA  'I56-4225-001 NRX-OPT Web'  (manu='Notifier' pm='B501RF')
--   SUPRIME   2 de 12 chunks de 'I56-4206-001 NRX Radio Thermals Web'  (manu='Notifier' pm='B501RF')
--   PRESERVA  UNIQUE=2, PARTIAL=6, COVERED_NO_TWIN=2
--   cobertura 0.50/0.72 · motivo del representante: empate metadata → más spans únicos (11 vs 7)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('721c3b21-9f21-4b56-995d-462b4f6e3aa3','a487dec9-0ec3-4408-ab55-accb2423c0b7','65246432-bac6-4cf0-ac02-f4d770f4ac92','a6d93291-43e7-464f-b0da-8b888f5a0ab0',0.9863,0.7838,0,'9cb99e9cabf514d56c745e0336f7e770','65246432__a6d93291'),
--   ('519c16b8-9d73-4e5a-8400-00cbae2916d4','6afc0d1f-560d-45da-94c9-0429128c42af','65246432-bac6-4cf0-ac02-f4d770f4ac92','a6d93291-43e7-464f-b0da-8b888f5a0ab0',1.0,1.0,0,'384787d22de7c96214e98ab9fbafcbc3','65246432__a6d93291'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 13: 153d05f2__9cbcc4fa   [T2-MISMA-MARCA]
--   CONSERVA  'MIEMI130.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   6 de 46 chunks de 'MIEMI120rev05.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=7, PARTIAL=32, COVERED_NO_TWIN=1
--   cobertura 0.62/0.71 · motivo del representante: empate metadata → más spans únicos (58 vs 44)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('0e6abe55-2726-404d-8349-8c6bb7df0bef','12f9fde3-b448-4f05-b52d-0c4a03839489','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',0.9474,0.716,0,'a5b49abad770a1bf3230182cae90b2bb','153d05f2__9cbcc4fa'),
--   ('9fcf26e7-b975-4eaf-b95e-499d7130b2d5','09476249-c016-4cf5-a2fa-c77d674babbd','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',1.0,0.6358,0,'86c16e402b372ad1fcb537e13f765712','153d05f2__9cbcc4fa'),
--   ('0c120e45-a546-4947-bf68-2924cdab2705','7e247206-4f33-46e7-84f4-011242a309e5','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',0.9882,0.8784,0,'48a2aa3380b1c5ae7f2802e640bc0bdc','153d05f2__9cbcc4fa'),
--   ('2c426c6f-57e9-4ba0-8f55-efdc2ad2f37f','d1613d5a-d641-4775-8a94-c8da1326571f','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',0.9769,0.9533,0,'d88dbb7e4adb15fd16eb7823da66c1fa','153d05f2__9cbcc4fa'),
--   ('22f91858-d6fa-4e55-8e59-81661e16487c','dfa6baef-ab59-4d89-adb6-db6628346ba1','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',0.9889,0.9176,0,'e2144ff61cd2c5b8dc8f070fb423102a','153d05f2__9cbcc4fa'),
--   ('dd4fd297-1fb9-4307-9421-ee2aa956a4f2','8bfa775c-a3fa-4b60-8556-81e0219da6e9','9cbcc4fa-fe19-4dc5-a2c6-d8fcbe606f92','153d05f2-81ed-496c-b6b2-8d699a591778',0.9527,0.8371,0,'4ec4ade3321598ddab1155bc3269e7bc','153d05f2__9cbcc4fa'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 14: 1e86c112__4bf442fb   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]
--   CONSERVA  'I56-2081-001ES 6500R(S) Manual'  (manu='System Sensor' pm='6500R')
--   SUPRIME   1 de 20 chunks de 'I56-2081-012 6500R(S)_ES'  (manu='Xtralis' pm='6500R')
--   PRESERVA  UNIQUE=6, PARTIAL=9, COVERED_NO_TWIN=4
--   cobertura 0.68/0.69 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'I56-2081-012 6500R(S)_ES' (más spans únicos (16 vs 14))
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('1475940a-ae7f-4c2d-9f1b-90cfc252ddf5','0498cd0a-0aca-479b-bdbb-c0999cda51ba','1e86c112-02a7-4c91-b64a-4d340601cd6a','4bf442fb-9f63-4205-a2f7-535a5055eac6',1.0,1.0,0,'e62a0ed8d7802f34c76d2b100d9d8190','1e86c112__4bf442fb'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 15: 3caeba69__a6d93291   [T2-MISMA-MARCA]
--   CONSERVA  'I56-4225-001 NRX-OPT Web'  (manu='Notifier' pm='B501RF')
--   SUPRIME   3 de 16 chunks de 'I56-4205-001 NRX-SMT3 Web'  (manu='Notifier' pm='B501RF')
--   PRESERVA  UNIQUE=3, PARTIAL=8, COVERED_NO_TWIN=2
--   cobertura 0.63/0.69 · motivo del representante: REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'I56-4225-001 NRX-OPT Web' (metadata 3/3, 11 spans únicos). Original por-par: empate metadata → más spans únicos (10 vs 7)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('b0938b50-71dd-4827-81ad-65959777e13a','2fb5fa0a-b09b-4897-8f9f-9c5c2891a3fd','3caeba69-e786-4fde-89c2-3249f44519ae','a6d93291-43e7-464f-b0da-8b888f5a0ab0',1.0,1.0,0,'df2caa8055376e6ec740543d8a1a7ccb','3caeba69__a6d93291'),
--   ('fd89253b-9d2e-49e7-acaf-bba726cf9f43','a487dec9-0ec3-4408-ab55-accb2423c0b7','3caeba69-e786-4fde-89c2-3249f44519ae','a6d93291-43e7-464f-b0da-8b888f5a0ab0',1.0,1.0,0,'776af76fe101fbcc40cc85ccbb749e26','3caeba69__a6d93291'),
--   ('0d0cb948-7b24-42ed-b938-c817e8267caa','6afc0d1f-560d-45da-94c9-0429128c42af','3caeba69-e786-4fde-89c2-3249f44519ae','a6d93291-43e7-464f-b0da-8b888f5a0ab0',1.0,0.8327,0,'5561101d2f865bb4724b79a2cf5bf85e','3caeba69__a6d93291'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 16: 0befac70__af770ec5   [T2-MISMA-MARCA]
--   CONSERVA  'MIE-MP-210.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 11 chunks de 'MIE-MI-220.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=5, PARTIAL=4
--   cobertura 0.07/0.69 · motivo del representante: empate metadata → más spans únicos (105 vs 7)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('364a687f-a3ca-4379-a8dd-82d5da7c3ba0','3c140682-581e-4542-b7c1-20421d337349','af770ec5-b3b8-4fdd-b8c0-282df17c28ab','0befac70-e041-4f8f-bf13-27678621c334',0.9428,0.7022,0,'4dc6bd51be2f314e9290789f44a0b2c1','0befac70__af770ec5'),
--   ('3fad8a0f-3cf4-42d3-8cb6-8aa9cdab1956','8ff427e4-316b-4695-8b2b-457319e3f3a0','af770ec5-b3b8-4fdd-b8c0-282df17c28ab','0befac70-e041-4f8f-bf13-27678621c334',0.9884,0.847,0,'89d828253c7445008a2343f2899a92fc','0befac70__af770ec5'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 17: f3e9aaa9__fea0ec1d   [T2-MISMA-MARCA]
--   CONSERVA  'MIE-MI-490.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 7 chunks de 'MIE-MI-480.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=2, PARTIAL=3
--   cobertura 0.62/0.67 · motivo del representante: empate metadata → más spans únicos (6 vs 4)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('badc4779-fb12-4381-8f25-2d338d46834a','dc7a67a9-c9be-41f1-8205-25b3ddfa9be9','fea0ec1d-2f2d-4b88-9b91-3e41a2234e46','f3e9aaa9-ffc2-4f2f-bb41-a61a971053e1',0.9399,0.8151,0,'8eeea9b3c83793536ae23fa7cd111882','f3e9aaa9__fea0ec1d'),
--   ('85d4dbfd-8aba-4dc0-8811-cb21729ae73a','beac1db0-f76d-40bf-ae9a-59d33f317b21','fea0ec1d-2f2d-4b88-9b91-3e41a2234e46','f3e9aaa9-ffc2-4f2f-bb41-a61a971053e1',1.0,1.0,0,'d49a30c45a023083c0fff6b294662823','f3e9aaa9__fea0ec1d'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 18: 0ef10ac7__7601da55   [T2-MISMA-MARCA]
--   CONSERVA  'MNDT626.pdf'  (manu='Notifier' pm='SMART 3')
--   SUPRIME   4 de 18 chunks de 'MNDT625.pdf'  (manu='Notifier' pm='SMART 3')
--   PRESERVA  UNIQUE=4, PARTIAL=9, COVERED_NO_TWIN=1
--   cobertura 0.49/0.67 · motivo del representante: empate metadata → más spans únicos (24 vs 16)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('86df92b5-c05c-436c-86c2-27c5bd24a43e','b60fbf81-32c3-4cc1-bb13-dd8341c5781b','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9556,0.8658,0,'6db4573b725d8e47454f5faabf8127dd','0ef10ac7__7601da55'),
--   ('62cd8227-933e-44a5-9bf7-04efe93a27fe','b56ee4b3-b7d9-49e3-813a-1046951e6ddb','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9698,0.6789,0,'9801b799b52fd1e7fda84312619e7d44','0ef10ac7__7601da55'),
--   ('4a98b418-ab93-4bb2-833d-fc78eda133e1','b1ce217d-a3b0-4177-9f0d-73e3fc42f19e','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9444,0.7955,0,'4f4d693c907b6b056caef6346f5d8180','0ef10ac7__7601da55'),
--   ('020ff008-608c-4aff-8103-1f88b4809b21','1524abf5-1ac0-4db1-8674-5b5580bead19','7601da55-96b9-4991-b97a-0b0ce9b44030','0ef10ac7-fb05-47bd-a85f-de393bbac45e',0.9658,0.68,0,'29754d329fd93e633aa531997e4f39c4','0ef10ac7__7601da55'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 19: 06887ff1__1d4f6e36   [T2-MISMA-MARCA]
--   CONSERVA  'MNDT516'  (manu='Notifier' pm='PL4')
--   SUPRIME   11 de 26 chunks de 'MNDT516_PL4_ESP-PORT'  (manu='Notifier' pm='PL4')
--   PRESERVA  UNIQUE=9, PARTIAL=5, COVERED_NO_TWIN=1
--   cobertura 0.36/0.67 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
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
-- PAR 20: 496ef3af__f3e9aaa9   [T2-MISMA-MARCA]
--   CONSERVA  'MIE-MI-490.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   2 de 6 chunks de 'MIE-MI-470.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=1, PARTIAL=3
--   cobertura 0.55/0.66 · motivo del representante: REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'MIE-MI-490.pdf' (metadata 2/3, 6 spans únicos). Original por-par: empate metadata → más spans únicos (6 vs 4)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('1c41c6fc-4c60-48df-870a-2d9bb6899d0b','dc7a67a9-c9be-41f1-8205-25b3ddfa9be9','496ef3af-6599-4f2e-9329-7ab6a3517c3f','f3e9aaa9-ffc2-4f2f-bb41-a61a971053e1',1.0,1.0,0,'d7dd5cb81044d826a1011fe0f1531ff7','496ef3af__f3e9aaa9'),
--   ('4b1d21e2-817b-4ac1-8d48-4d082da173a9','416e6d08-16ad-4794-8afb-19e98b035e84','496ef3af-6599-4f2e-9329-7ab6a3517c3f','f3e9aaa9-ffc2-4f2f-bb41-a61a971053e1',0.989,0.7576,0,'231403091383b7e448900ad09f997eff','496ef3af__f3e9aaa9'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 21: 1e2b058a__4421642f   [T2-MISMA-MARCA]
--   CONSERVA  'MNDT710_B.pdf'  (manu='Spectrex' pm='20/20U, 20/20UB')
--   SUPRIME   6 de 41 chunks de 'MNDT720.pdf'  (manu='Spectrex' pm='20/20L, 20/20LB')
--   PRESERVA  UNIQUE=14, PARTIAL=21
--   cobertura 0.56/0.66 · motivo del representante: empate metadata → más spans únicos (36 vs 30)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('c5cda265-afed-447a-881f-21e4ccc39a38','3feb06af-4101-494d-b564-837f22aa5308','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',0.951,0.6667,0,'9272c2688c258d8c4db9dc7b3d4543af','1e2b058a__4421642f'),
--   ('750ece5a-721a-4683-bd9c-bf43d617fbbc','574af291-4586-4994-8d40-137c6ffb712f','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',1.0,0.9355,0,'8243e5e09884f4023fe8951caad45cab','1e2b058a__4421642f'),
--   ('ecbd4102-154e-433e-82aa-a6f92a8315ee','709611a5-3fb7-474b-8383-0becdfbbb535','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',0.9678,0.7467,0,'0b305f133340d00427c93bf34940f866','1e2b058a__4421642f'),
--   ('d3fda059-590f-45f5-851c-cc8058b2bfdf','eee344d5-d329-4520-af6a-9b2460513693','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',1.0,1.0,0,'1018867779ef8ff22b7dc62c66c105fc','1e2b058a__4421642f'),
--   ('5dfb30b6-21bc-4f10-a8f3-b1474a54a0ac','4bf70e81-e1c2-4f46-9b99-72b9dbaebae3','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',0.9446,0.6424,0,'ab91c42921e84967bfb3780808dd5981','1e2b058a__4421642f'),
--   ('ac668909-fb9d-4593-a9c7-5470e8f9aab5','db9dd780-f34e-4186-971a-fa8258a49866','1e2b058a-4951-4d67-b9c9-61e009ccd59f','4421642f-29b2-4cc9-af08-2eb1f393316f',0.984,0.9781,0,'d06047297490f2b63a059f178031660e','1e2b058a__4421642f'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 22: 5e483105__71654eda   [T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA]
--   CONSERVA  'MN-DT-951_v7.2'  (manu='Notifier' pm='unknown')
--   SUPRIME   1 de 57 chunks de 'TG-Honeywell_Usuario'  (manu='Morley' pm='TG-Honeywell')
--   PRESERVA  UNIQUE=33, PARTIAL=17, COVERED_NO_TWIN=6
--   cobertura 0.40/0.66 · motivo del representante: metadata auto-soportada (2/3 vs 1/3)
--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría 'TG-Honeywell_Usuario' (más spans únicos (61 vs 24))
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('3036bc47-d185-480e-a27f-f6b463b4961b','ff789f7c-1aef-43a3-9c98-5930446b5e33','71654eda-7c94-4aec-9ce3-4310fb254e7e','5e483105-7539-45be-9858-d50ecbdc5cd0',0.9759,0.6412,0,'24ccf2fcc3da55af3428f6f3d70e4230','5e483105__71654eda'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 23: 29a94dea__30c75a7c   [T2-MISMA-MARCA]
--   CONSERVA  'MIE-MI-431rv2_1.pdf'  (manu='Morley' pm='unknown')
--   SUPRIME   1 de 8 chunks de 'MIE-MI-450.pdf'  (manu='Morley' pm='unknown')
--   PRESERVA  UNIQUE=7
--   cobertura 0.33/0.65 · motivo del representante: empate metadata → más spans únicos (17 vs 7)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('4fa0ce82-f5e4-417c-86b4-90393901464c','582fc396-ab79-4fdb-a3b5-1293251839e5','29a94dea-c2a7-4672-b028-b3e776d1de6d','30c75a7c-36ef-4160-bd76-99d869d7ac77',1.0,1.0,0,'7ca1870985090506e3762414e37b120f','29a94dea__30c75a7c'),
-- ────────────────────────────────────────────────────────────────────────────────────────────────
-- PAR 24: af5d5d01__b9c694a3   [T2-MISMA-MARCA]
--   CONSERVA  '00-3280-501-4009-05_r005_2x-a_series_installation_manual_es.pdf'  (manu='Aritech' pm='2X-A')
--   SUPRIME   5 de 44 chunks de '00-3280-505-4009-04_r004_2x-a_series_operation_manual_es.pdf'  (manu='Aritech' pm='2X-A')
--   PRESERVA  UNIQUE=16, PARTIAL=16, COVERED_NO_TWIN=7
--   cobertura 0.20/0.62 · motivo del representante: metadata auto-soportada (3/3 vs 1/3)
--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo (quita el '-- ' inicial)
--   ('571d0fe8-25b5-4cfb-8aab-8426fc867437','39e830d7-fb0d-4d5d-a919-85a6deb3e957','b9c694a3-163f-400f-9785-6e34790fb880','af5d5d01-d5a9-48df-9acb-ae4994d19251',0.9956,0.7296,0,'94e49ff8d7b7abb93a996e55a053a2e5','af5d5d01__b9c694a3'),
--   ('e9cd2d16-f197-482c-9655-a9ed72eeb5f7','f83e4e02-7eb8-4eb3-8c8d-74ee89ed4c50','b9c694a3-163f-400f-9785-6e34790fb880','af5d5d01-d5a9-48df-9acb-ae4994d19251',0.9606,0.7051,0,'d501031f1ee538c339b99e8b70568bf1','af5d5d01__b9c694a3'),
--   ('cfc0bf85-19a5-41a8-8d72-e5be636f2ece','760f421a-98dd-4fad-9575-367db7dc4edd','b9c694a3-163f-400f-9785-6e34790fb880','af5d5d01-d5a9-48df-9acb-ae4994d19251',0.9508,0.7445,0,'7d898aa3b47a04dd80e5acf7433f7160','af5d5d01__b9c694a3'),
--   ('6c863a67-bf48-4a69-a7d4-0d3498aa14e0','a33a3d5f-a963-40a5-87d5-e6792599d7e7','b9c694a3-163f-400f-9785-6e34790fb880','af5d5d01-d5a9-48df-9acb-ae4994d19251',0.97,0.8561,0,'38d66de82c4d5277dc09b75ee1b9efc5','af5d5d01__b9c694a3'),
--   ('f33a1620-4fbc-4d9d-824f-e666ebea0623','29b4c8b8-3699-4a7f-98e9-b96d8d379fec','b9c694a3-163f-400f-9785-6e34790fb880','af5d5d01-d5a9-48df-9acb-ae4994d19251',0.9796,0.8939,0,'9f519cabe867f1d646874f2bae1a64fc','af5d5d01__b9c694a3'),
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

-- ROLLBACK post-COMMIT:
--   UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of
--     FROM _s287_dedup_backup b WHERE c.id = b.id;

COMMIT;   -- <-- para dry-run: ROLLBACK
