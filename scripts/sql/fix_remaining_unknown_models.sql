-- Fix remaining 17,838 Notifier chunks with product_model='unknown'
-- Generated from content analysis of first chunks per source_file
-- Run in Supabase SQL Editor

-- === Centrales de incendios ===
UPDATE chunks SET product_model = 'ID50/60' WHERE source_file = 'MIDT156' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MCDT191' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MFDT190' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID50/60' WHERE source_file = 'MFDT156' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = 'HOP-138-8ES  issue 6_01-2026_Co' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = 'HOP-338-9PT-issue 4_01-2026_Op' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = 'HOP-338-9ES issue 4_01-2026_Op' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = '4188-1125-ES issue 5_11-2025_Li' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = '4188-1132-ES issue 3_04_2025_Qref' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = '4188-1122-ES issue 4_04-2025_Cyb' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'INSPIRE' WHERE source_file = 'Actualizacion del firmware de INSPIRE a R1.35' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3008' WHERE source_file = 'MIDT193_ID3008-001_Instal_esp' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3004' WHERE source_file = 'MIDT192_ID3004-001_Instal_esp' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Central conv. 2-8 zonas' WHERE source_file = '997-493-002-2' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Central conv. 2-8 zonas' WHERE source_file = '997-493-002-2_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Central conv. 2-8 zonas' WHERE source_file = '997-493-002-2_2' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'MN-DT-530' WHERE source_file = 'MNDT530' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'MN-DT-530' WHERE source_file = 'MNDT530_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Detectores de aspiración ===
UPDATE chunks SET product_model = 'VESDA-E VES' WHERE source_file = '35006_03_VESDA-E_VES-A10-P_Product_Guide_A4_Spanish_lores' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'VESDA-E VES' WHERE source_file = '35007_03_VESDA-E_VES-A00-P_Product_Guide_A4_Spanish_lores' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'VESDA-E VEU' WHERE source_file = '33979_12_VESDA-E_VEU-A10_Product_Guide_A4_Spanish_lores' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ASD' WHERE source_file = 'ASD Cold Environments_SP' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ASD' WHERE source_file = 'ASD Harsh Environments_SP' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ASD' WHERE source_file = 'ASD in Custodial Applications_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Central PEARL ===
UPDATE chunks SET product_model = 'PEARL' WHERE source_file = '997-669-005-3_Instal-Comm_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'PEARL' WHERE source_file = '997-671-005-3_Configuration_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'PEARL' WHERE source_file = '997-670-005-3_Operating_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'PEARL' WHERE source_file = '997-671-007-3_Configuration_PT' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'PEARL' WHERE source_file = '997-670-007-3_Operating_PT' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Detectores puntuales / gas ===
UPDATE chunks SET product_model = 'LTS2' WHERE source_file = 'MNDT1071' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'LTS2' WHERE source_file = 'MNDT1071_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'S20/20MI' WHERE source_file = 'MNDT696' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'S20/20MI' WHERE source_file = 'MADT696_01' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'FS-Series' WHERE source_file = 'MADT606' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'FS-1100' WHERE source_file = 'TM380002_RevIMarch2016_FS-1100' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'FS-1300' WHERE source_file = 'TM380202_AApril2016_FS-1300' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'HSF-280' WHERE source_file = 'MF_HSF_280_rv004' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Sirenas y balizas ===
UPDATE chunks SET product_model = 'NFS2-8' WHERE source_file = 'MADT015_02' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'LCD-8200' WHERE source_file = 'LCD-8200-manu-spa' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'AM-LCD' WHERE source_file = 'AM-LCD manual de instalacion y usuario RV 0' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Módulos y gateways ===
UPDATE chunks SET product_model = 'iBox-BACnet' WHERE source_file = 'MNDT960I_iBox-BACnet' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'iBox-Modbus' WHERE source_file = 'MNDT958' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'iBox-Modbus' WHERE source_file = 'MN-DT-958I_iBox-MBS-NID3000' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'TG-IP1-SEC' WHERE source_file = 'HLSI_MN-DT-1412_TG-IP1-SEC_MN' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'UCIP' WHERE source_file = 'HLSI-MA-192_05 Quick Start Guide UCIP GPRS_GB' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'MI-DT-1500' WHERE source_file = 'MIDT1500_A' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'TG-Honeywell' WHERE source_file = 'Enlace entre TG' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'AgileIQ' WHERE source_file = 'I56-3909-010_A_AgileIQ_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Accesorios - Electroimanes ===
UPDATE chunks SET product_model = 'Art.1330-1345' WHERE source_file = 'MNDT1102' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1330-1345' WHERE source_file = 'MNDT1102_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1330-1345' WHERE source_file = 'MNDT1102_2' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1330-1345' WHERE source_file = 'MNDT1102_3' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1350/1360' WHERE source_file = 'MNDT1103' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1370/1380' WHERE source_file = 'MNDT1104' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1370/1380' WHERE source_file = 'MNDT1104_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Art.1369' WHERE source_file = 'MNDT1105' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'Aerosol CO' WHERE source_file = 'MNDT1200' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === Sistemas de extinción ===
UPDATE chunks SET product_model = 'WFDN' WHERE source_file = 'WFDN_i56-4052-000r_ES' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- === ID3000 series (MADT190_xx) ===
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_02' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_02_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_07' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_07_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_09' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_10' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_11' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_13' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190_14' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190P_02' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'MADT190P_02_1' AND manufacturer = 'Notifier' AND product_model = 'unknown';
UPDATE chunks SET product_model = 'ID3000' WHERE source_file = 'LEER PRIMERO_MADT951_10' AND manufacturer = 'Notifier' AND product_model = 'unknown';

-- Verify result
SELECT count(*) as remaining_unknown FROM chunks WHERE manufacturer = 'Notifier' AND product_model = 'unknown';
