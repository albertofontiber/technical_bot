-- s285 conflicts-apply — corrección adjudicada de doc_type/language sobre `documents`
-- GENERADO por scripts/s285_conflicts_apply_gen.py (determinista desde git; ver docstring).
-- Adjudicación: packet s285_conflicts_packet_v2.md + hilo 28-jul (OK Alberto; VESDA/VLF;
-- RS232 retirado; Puedo-anular='operacion'; UCIP-Tabla language='es').
-- Esperado: 75 filas UPDATE · 19 doc_type · 65 language.
-- GUARD ATÓMICO: los predicados de before-image viven en el WHERE del UPDATE; si CUALQUIER
-- fila no coincide, el conteo falla y la transacción entera aborta (all-or-nothing).
-- Dry-run: cambia el COMMIT final por ROLLBACK.

BEGIN;

CREATE TEMP TABLE conf_staging (
  document_id  uuid PRIMARY KEY,
  source_file  text NOT NULL,
  touch_doc_type boolean NOT NULL,
  set_doc_type text,
  expect_doc_type text,
  touch_language boolean NOT NULL,
  set_language text,
  expect_language text
) ON COMMIT DROP;

INSERT INTO conf_staging VALUES
  ('144d759a-400f-44e7-8496-e5ffd706ec5e', '11369_22_VESDA_VLF-250_Product_Guide_A4_Spanish_lores', true, 'instalacion', 'guia_usuario', false, NULL, NULL),
  ('e2c7c875-aa95-4b3c-9ce2-3a2988f94ca8', '11370_17_VESDA_VLF-500_Product_Guide_A4_Spanish_lores', true, 'instalacion', 'guia_usuario', false, NULL, NULL),
  ('b22fdb7f-f9e9-49d0-9e40-e840c24d25e9', '33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores', true, 'instalacion', 'hoja_datos', false, NULL, NULL),
  ('17d4b914-fa21-4b41-a928-bafe1846528a', '997-671-005-3_Configuration_ES', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('eb749df8-87db-4800-90dd-7d65889822fa', 'Averia-de-resistencia-de-baterias-en-central-DXc', false, NULL, NULL, true, 'es', 'en'),
  ('348c4ec1-210a-441a-9ce7-02014a51f26d', 'CAD-250_Manual-Configuracion-MC-380-es-2026-c', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('23f0e4d2-5fd6-4f7c-992c-82584f311745', 'CAD-250_Manual-software-configuracion-MS-416-es-2026-b', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('e8b63990-d547-4fc3-ae41-bf6cdfe3c626', 'Como-configurar-correos-en-un-TG-HONEYWELL', true, 'configuracion', 'programacion', true, 'es', 'en'),
  ('8b2aa620-213b-49b4-a2a7-15d097ad7484', 'Como-solucionar-la-incidencia-TABLE-IS-FULL-en-el-TG', false, NULL, NULL, true, 'es', 'en'),
  ('df5fcf75-fa85-415b-9c08-cf30401c8f90', 'Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO', false, NULL, NULL, true, 'es', 'de'),
  ('a04eafd1-48d0-4ed6-9de8-4ff93ca6a3da', 'Compatibilidad-entre-equipos-Notifier-y-Morley', false, NULL, NULL, true, 'es', 'en'),
  ('1bc55fe2-3f36-455d-9f7a-3f600200a94f', 'Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus', true, 'configuracion', 'programacion', true, 'es', 'en'),
  ('06480ab0-ba4d-45a6-8ba9-f0842f278421', 'DXC-Como-conectar-una-sirena-de-lazo', false, NULL, NULL, true, 'es', 'de'),
  ('edbcb1ab-eb05-42ba-ba4f-83bfd3a673bc', 'DXC-Connexion-Como-programar-una-salida-de-averia-general', false, NULL, NULL, true, 'es', 'de'),
  ('c93e42ea-725c-4401-8ad0-233e654ffa31', 'DXC-Connexion-Compatibilidad-de-programas-con-versiones', false, NULL, NULL, true, 'es', 'de'),
  ('b2b94062-4bc4-49ff-ba98-9b6db305fbec', 'DXC-Connexion-Instalacion-y-configuracion-del-modulo-de-comunicacion-RS232', false, NULL, NULL, true, 'es', 'de'),
  ('c1a3d6cb-a9c9-4db4-983a-33477d1dbb33', 'DXC-Porque-al-activan-elementos-en-alarma-no-se-enciende-su-led', false, NULL, NULL, true, 'es', 'en'),
  ('df8ba722-0fb4-4f4c-ab04-03642009839f', 'DXC-Puedo-anular-la-clave-de-usuario-y-acceder-directamente-al-teclado', true, 'operacion', 'usuario', true, 'es', 'de'),
  ('56c8d6f1-a7c4-431b-89a7-58e7e9d373fe', 'DXC-puedo-cambiar-la-clave-de-nivel-3', false, NULL, NULL, true, 'es', 'de'),
  ('24dbcd19-dada-4e04-b8aa-63bbd5f7db9e', 'DXc-Configuracion-de-la-tarjeta-232-aislada-para-comunicarse-con-el-TG', true, 'configuracion', 'programacion', true, 'es', 'de'),
  ('c4d2e158-cc93-49a7-81a2-9dd4ea2358e9', 'DXc-Connexion-Como-solucionar-la-averia-de-Ent-Placa-1-o-2', false, NULL, NULL, true, 'es', 'de'),
  ('2c970f38-1bf8-47d7-a005-e19f3f03839f', 'DXc-Opciones-de-disparo-de-programas-Matrices', false, NULL, NULL, true, 'es', 'de'),
  ('50fbe217-23b4-49ed-bfbe-3de19869db12', 'DXc-Tipos-Abreviaturas-de-equipos', false, NULL, NULL, true, 'es', 'de'),
  ('52c3ab31-1ac3-4a8d-a758-8c66c3dcb85d', 'DXc-Tipos-de-accion-para-entradas', false, NULL, NULL, true, 'es', 'en'),
  ('5e878ee7-53eb-4b03-bda3-5fd5de306bba', 'DXc_Connexion Averia-de-resistencia-de-baterias', false, NULL, NULL, true, 'es', 'de'),
  ('accbda3e-465f-4f0a-ad17-5c62c24835e7', 'Eventos-Averias-de-Equipos-en-DXc', false, NULL, NULL, true, 'es', 'en'),
  ('43e2ec68-c0f0-4098-905e-8ddc51eed4b7', 'Fallo-I2C-en-RP1rSupra', false, NULL, NULL, true, 'es', 'en'),
  ('aacf3f31-49d4-4128-98f9-887189fad761', 'Finales-de-linea-de-las-centrales-convencionales', false, NULL, NULL, true, 'es', 'de'),
  ('80e1b7d2-1455-454d-8545-18b858ba9a70', 'HOP-138-8ES  issue 6_01-2026_Co', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('5cfbede1-6742-4890-9881-7f3858e8f3cc', 'ITAC-Como-asignar-la-direccion-en-el-ITAC', false, NULL, NULL, true, 'es', 'en'),
  ('eb0e9e0a-4df5-4576-ac38-ddb0fccbc589', 'ITAC-no-reconocido-por-la-Central', false, NULL, NULL, true, 'es', 'pt'),
  ('e43724ba-6bd4-46c7-982f-02b9c2a765e1', 'MIW-INT-Asignar-de-direccion-pasarela-detectores-y-Modulos-Via-radio-Morley', false, NULL, NULL, true, 'es', 'de'),
  ('f204e658-e7ca-4f2c-a80a-3e95d58e31ea', 'MIW-INT-Averia-de-TAMPER', false, NULL, NULL, true, 'es', 'de'),
  ('ecc2dbc2-825b-4454-bc23-f3fe2f02751b', 'MIW-INT-Dar-de-alta-un-detector', false, NULL, NULL, true, 'es', 'de'),
  ('3e9d9c12-1b78-48d1-9434-6ef5942b13cf', 'MIW-INT-La-central-indica-averia-de-datos-de-sensor', false, NULL, NULL, true, 'es', 'de'),
  ('ce839851-ac35-4e8e-8724-21d28f7e3257', 'MIW-INT-Mensaje-de-error-LOEr-via-radio-Morley', false, NULL, NULL, true, 'es', 'de'),
  ('cdb441ec-920d-4487-a772-eea538a6ad58', 'MIW-al-sustituir-las-baterias-de-un-equipo-se-necesita-programarlo-de-nuevo', false, NULL, NULL, true, 'es', 'de'),
  ('0131512d-e62d-4c40-b6a6-2c776760c5cc', 'Morley-Se-pueden-pasar-programaciones-de-ZX-y-Dimension-a-Connexion-DXC', false, NULL, NULL, true, 'es', 'de'),
  ('10a840b5-bf48-40e5-a803-02450f1dc143', 'NFS-SUPRA-VISION-PLUS-2-Como-solucionar-el-Fallo-de-alimentacion', false, NULL, NULL, true, 'es', 'de'),
  ('8b27b183-9e64-438a-bfa0-e0bed0747381', 'NFS-SUPRA-VSN12-2PLUS-Funcionamiento-de-la-central-en-modo-prueba', false, NULL, NULL, true, 'es', 'en'),
  ('156db1c3-8df4-45c1-9c66-10e75c2d59f5', 'NFS-SUPRA-VSN2-PLUS-Entrada-Digital', false, NULL, NULL, true, 'es', 'en'),
  ('767bde0f-e094-4bdb-a08b-e08cc8e5e0ba', 'Niveles-de-control-de-acceso-de-la-central-DXC-CONEXION', false, NULL, NULL, true, 'es', 'de'),
  ('8e8d6e3b-84ec-4cf7-b88a-39f3141e9b7c', 'No-funcionan-las-teclas-de-la-central-VSN', false, NULL, NULL, true, 'es', 'de'),
  ('6a88902d-573c-48be-954b-b305d5236380', 'No-puedo-hacer-Rearme-o-silenciar-sirenas-en-la-VSN-LT', false, NULL, NULL, true, 'es', 'en'),
  ('dc5aae73-da3f-4ff7-a9dd-7f993c5c1bf2', 'Poner-la-contraseña-por-defecto-del-programa-de-gestion-grafica-TG', false, NULL, NULL, true, 'es', 'pt'),
  ('d07cfed0-c5a4-4e07-a807-e5f725992d06', 'Puesta-en-marcha-repetidor-ZXrA-en-central-CONNEXION', false, NULL, NULL, true, 'es', 'en'),
  ('4eb9710c-8fa2-4ff3-9052-2704d666dcb9', 'RP1R-Supra_VSN-RP1R-PLUS2-Averia-Rl_y_Fallo-de-sistema-intermitente', false, NULL, NULL, true, 'es', 'de'),
  ('e0c48b01-7c25-46f9-83ff-65a52c08181e', 'RP1r-Supra-VSN-RP1R-PLUS2-Como-cambiar-el-tipo-de-final-del-linea', false, NULL, NULL, true, 'es', 'de'),
  ('45b0fc60-4924-45cc-962d-5e8d653cbeb8', 'Rearme-remoto-en-central-DXc-Connexion', false, NULL, NULL, true, 'es', 'en'),
  ('669b0974-b043-45af-af88-0af12aa65bb5', 'Relacion-de-producto-obsoleto-de-Morley-IAS-by-Honeywell', false, NULL, NULL, true, 'es', 'de'),
  ('9077a0cb-0b51-440f-8f94-6615f84d2624', 'TG-ATENCION-El-sistema-no-encuentra-la-proteccion-del-TG', false, NULL, NULL, true, 'es', 'en'),
  ('d06af30d-1ed9-49b3-8a0a-88f13fa160b2', 'TG-Como-borrar-elementos-de-un-plano', false, NULL, NULL, true, 'es', 'de'),
  ('1e5830eb-b2e0-4626-b785-f7df0dc82f21', 'TG-Como-exportar-el-historico-desde-el-programa-de-gestion-grafica', false, NULL, NULL, true, 'es', 'de'),
  ('065e84ed-6982-4a4b-be44-43de34ca415b', 'TG-Como-hacer-una-copia-de-seguridad-del-proyecto', false, NULL, NULL, true, 'es', 'de'),
  ('39795638-b4ec-4bbe-a68d-76d27f2d5d2b', 'TG-Como-solucionar-problema-de-Error-CRC', false, NULL, NULL, true, 'es', 'de'),
  ('26df1e27-96c2-497e-aed1-5f5f47f6abb9', 'TG-GSM-Fallo-al-enviar-SMS-desde-TG', false, NULL, NULL, true, 'es', 'en'),
  ('f0b9b790-f2e2-40cb-b793-289e11b82f4f', 'TG-IP-1-SEC-Que-direccion-IP-tiene-por-defecto', false, NULL, NULL, true, 'es', 'pt'),
  ('d6bfca01-9d08-4a20-91ce-5284b6b6ee67', 'TG-Que-clave-tiene-si-se-instala-en-idioma-Ingles', false, NULL, NULL, true, 'es', 'en'),
  ('60a23f8e-4dca-434a-b158-67d5c6d5b7d4', 'TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCIAS', false, NULL, NULL, true, 'es', 'de'),
  ('5c223ffe-4296-457c-95cb-1023b870e2a6', 'UCIP-Borrado-a-valores-de-fabrica', false, NULL, NULL, true, 'es', 'de'),
  ('c0b1e530-f0ee-4060-8f0a-1ad39b2d5dfe', 'UCIP-Borrar-configuracion-completa', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('ca05027c-6814-4811-a7fb-0db800b6bcbf', 'UCIP-Borrar-datos-de-CRA1-o-2', false, NULL, NULL, true, 'es', 'de'),
  ('7f2b752c-4f10-41af-8d23-8c7362d13996', 'UCIP-Cambio-de-puerto-TCP-en-GPRS', false, NULL, NULL, true, 'es', 'en'),
  ('e3323da7-65ff-4927-a2db-edb651fb8e8d', 'UCIP-Cambio-de-puerto-TCP-red-LAN', false, NULL, NULL, true, 'es', 'de'),
  ('d90756e2-e023-44ce-be67-9b7b3e0a79c5', 'UCIP-Como-configurar-envio-de-eventos-por-equipo', true, 'configuracion', 'programacion', true, 'es', 'en'),
  ('228ffa26-296c-469e-a879-f6a0d9aec575', 'UCIP-Como-enviar-datos-de-equipos-y-no-solo-eventos-de-zonas', false, NULL, NULL, true, 'es', 'en'),
  ('6ea38997-d7c1-41f3-a5fa-a4e714966e78', 'UCIP-Configuracion-CRA1', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('d38e4f08-102d-4f11-b9a0-599b2ff4a4ad', 'UCIP-Configurar-PIN-tarjeta-SIM', true, 'configuracion', 'programacion', false, NULL, NULL),
  ('a4d46ae3-226e-46c1-a98b-201494b4c234', 'UCIP-Configurar-envio-de-SMS', true, 'configuracion', 'programacion', true, 'es', 'en'),
  ('969c3f17-c429-4aff-9bbf-c04f6e55fbb8', 'UCIP-Configurar-puerto-UART-de-UCIP', true, 'configuracion', 'programacion', true, 'es', 'de'),
  ('0e11bf91-bb4d-43c3-8bab-9dd5b612787b', 'UCIP-No-conecta-por-IP', false, NULL, NULL, true, 'es', 'pt'),
  ('4775e676-1974-4077-83f7-2c4e6cb9236a', 'UCIP-Programacion-IP-de-equipo', true, 'configuracion', 'programacion', true, 'es', 'de'),
  ('0aab17df-dfe0-4a45-9a01-d47d77f251e1', 'UCIP-Que-datos-necesito-de-la-receptora', false, NULL, NULL, true, 'es', 'de'),
  ('c3a3eb01-e91f-4732-9beb-b5e0cd011c44', 'UCIP-Tabla-de-compatibilidad-con-receptoras-y-centrales', false, NULL, NULL, true, 'es', 'de'),
  ('f255ef6e-e3ef-457b-b299-c1c9c6124bff', 'UCIP-Ver-configuracion-de-equipo', true, 'configuracion', 'programacion', true, 'es', 'de');

DO $$
DECLARE n_stage int; n_missing int; n_map int; n_drift int;
BEGIN
  SELECT count(*) INTO n_stage FROM conf_staging;
  IF n_stage <> 75 THEN RAISE EXCEPTION 'staging % <> 75', n_stage; END IF;

  SELECT count(*) INTO n_missing FROM conf_staging s
    LEFT JOIN documents d ON d.id = s.document_id
    WHERE d.id IS NULL OR d.status <> 'active';
  IF n_missing <> 0 THEN RAISE EXCEPTION '% document_id inexistentes o no-active', n_missing; END IF;

  -- correspondencia source_file <-> document_id (anti id-equivocado)
  SELECT count(*) INTO n_map FROM conf_staging s
    WHERE NOT EXISTS (SELECT 1 FROM chunks_v2 c
                      WHERE c.document_id = s.document_id AND c.source_file = s.source_file);
  IF n_map <> 0 THEN RAISE EXCEPTION '% filas sin chunk que ligue source_file<->document_id', n_map; END IF;

  -- pre-check informativo de deriva (el guard REAL es el WHERE del UPDATE)
  SELECT count(*) INTO n_drift FROM conf_staging s JOIN documents d ON d.id = s.document_id
    WHERE (s.touch_doc_type AND d.doc_type IS DISTINCT FROM s.expect_doc_type)
       OR (s.touch_language AND d.language IS DISTINCT FROM s.expect_language);
  IF n_drift <> 0 THEN RAISE EXCEPTION 'DERIVA: % filas con valor actual != esperado — NO se aplica nada', n_drift; END IF;
END $$;

CREATE TEMP TABLE conf_audit (
  document_id uuid, source_file text,
  set_doc_type text, expect_doc_type text, touch_doc_type boolean,
  set_language text, expect_language text, touch_language boolean
) ON COMMIT DROP;

WITH upd AS (
  UPDATE documents d SET
    doc_type = CASE WHEN s.touch_doc_type THEN s.set_doc_type ELSE d.doc_type END,
    language = CASE WHEN s.touch_language THEN s.set_language ELSE d.language END
  FROM conf_staging s
  WHERE d.id = s.document_id
    AND (NOT s.touch_doc_type OR d.doc_type IS NOT DISTINCT FROM s.expect_doc_type)
    AND (NOT s.touch_language OR d.language IS NOT DISTINCT FROM s.expect_language)
  RETURNING d.id, s.source_file, s.set_doc_type, s.expect_doc_type, s.touch_doc_type,
            s.set_language, s.expect_language, s.touch_language
)
INSERT INTO conf_audit SELECT * FROM upd;

DO $$
DECLARE n_upd int; n_dt int; n_lang int;
BEGIN
  SELECT count(*) INTO n_upd FROM conf_audit;
  SELECT count(*) INTO n_dt   FROM conf_audit WHERE touch_doc_type;
  SELECT count(*) INTO n_lang FROM conf_audit WHERE touch_language;
  RAISE NOTICE 's285 conflicts-apply: updated=% doc_type=% language=%', n_upd, n_dt, n_lang;
  IF n_upd  <> 75 THEN RAISE EXCEPTION 'updated % <> 75 (deriva concurrente o id perdido) — la transaccion aborta entera', n_upd; END IF;
  IF n_dt   <> 19 THEN RAISE EXCEPTION 'doc_type % <> 19', n_dt; END IF;
  IF n_lang <> 65 THEN RAISE EXCEPTION 'language % <> 65', n_lang; END IF;
END $$;

SELECT document_id, source_file, set_doc_type, expect_doc_type, set_language, expect_language
FROM conf_audit ORDER BY source_file;

COMMIT;   -- <-- para dry-run: cambiar por ROLLBACK
