# Muestra de salida del transform (REGLA de granularidad) — para revisión del dúo

Procesados 985 docs reconciliados → 2530 filas de modelo (484 candidates, 30 de split de compuestos).

Cada doc: identidad reconciliada + lista de productos (canonical + aliases). Verificar: ¿R3 partió bien (sin over-split 3G/3D)? ¿canonical = nombre comercial limpio, SKU en aliases? ¿candidate marca bien las sobre-inclusiones de 1 solo modelo? ¿pierde info?


## `085501821n_DS10_Installation_manual_D-GB_F_IT`  [agree]
  identity: brand='unknown' oem='unknown'
    [prim/both] **DS 10**  ⟵ aliases: type DS 10, DS series, sounders of type series DS
    [prim/both] **DS 5**  ⟵ aliases: type DS 5, DS series, sounders of type series DS
    [seco/both ⟵split(DS 5 / DS 10 - TAS)] **DS 10 -TAS**  ⟵ aliases: Version 1 (DS 5 / DS 10 - TAS)
    [seco/both ⟵split(DS 5 / DS 10 - TAV)] **DS 10 -TAV**  ⟵ aliases: Version 2 (DS 5 / DS 10 - TAV)
    [seco/both] **DS 10-3G/3D**  ⟵ aliases: DS 10 -3G/ 3D, DS 5 -3G/ 3D, -3G/ 3D, special versions for explosion hazard zones 2 and 22
    [seco/both] **DS 10-GL**  ⟵ aliases: -GL-Version, Germanischer Lloyd version, DS 10 -GL-Version, GL-Version
    [seco/both ⟵split(DS 5 / DS 10 - TAS)] **DS 5 -TAS**  ⟵ aliases: Version 1 (DS 5 / DS 10 - TAS)
    [seco/both ⟵split(DS 5 / DS 10 - TAV)] **DS 5 -TAV**  ⟵ aliases: Version 2 (DS 5 / DS 10 - TAV)
    [seco/gpt ⟂candidate] **DS 5 -3G/3D**  ⟵ aliases: DS 5 -3G/ 3D, special versions for explosion hazard zones 2 and 22
    [seco/gpt ⟂candidate] **DS 5 -GL**  ⟵ aliases: DS 5 -GL-Version, GL-Version

## `15090SP`  [superset]
  identity: brand='Notifier' oem='Notifier'
    [prim/both] **NRT-586T**  ⟵ aliases: NRT, Terminal de Informe de Red, 586T, Terminal Reportera de Red, Terminal de Informe de la Red
    [seco/gpt ⟂candidate] **AFP-200**  ⟵ aliases: AFP200
    [seco/gpt ⟂candidate] **AFP-300**  ⟵ aliases: AFP300, AFP 300/400
    [seco/gpt ⟂candidate] **AFP-400**  ⟵ aliases: AFP400, AFP 300/400
    [seco/gpt ⟂candidate] **AFP1010**  ⟵ aliases: 
    [seco/gpt ⟂candidate] **AM2020**  ⟵ aliases: 
    [seco/gpt ⟂candidate] **HSP-121B**  ⟵ aliases: protector de la línea eléctrica HSP-121B
    [seco/gpt ⟂candidate] **LP-2**  ⟵ aliases: opción LP-2, Tablero del LP-2, Bolígrafo tipo Luz, placa de opción del LP-2
    [seco/gpt ⟂candidate] **MON-17B**  ⟵ aliases: MON-17B/21, Monitor de 17pulgadas (431.8 mm) (MON-17B)
    [seco/gpt ⟂candidate] **MON-21**  ⟵ aliases: Monitor de 21pulgadas (533.4 mm) (MON-21)
    [seco/opus ⟂candidate] **NRT-586TF**  ⟵ aliases: Enlace de fibra optica de la NRT
    [seco/opus ⟂candidate] **NRT-586TW**  ⟵ aliases: Enlace del Cable de datos de la NRT
    [seco/opus ⟂candidate] **NRT-586TWF**  ⟵ aliases: Enlace de fibra optica y cable de la NRT
    [seco/gpt ⟂candidate] **NRT-NET**  ⟵ aliases: tarjeta interfaz de red, tarjeta interfaz de la NRT-NET
    [seco/gpt ⟂candidate] **PCLB-5**  ⟵ aliases: Abrazadera del Cable de Energía, gabinete del PCLB-5, cubierta del PCLB-5
    [seco/gpt ⟂candidate] **PRN-4**  ⟵ aliases: impresora PRN-4

## `55310008 Manual Tarjeta Modbus TMD-100 Instalacion ES FR GB `  [agree]
  identity: brand='unknown' oem='unknown'
    [prim/both] **TMD-100**  ⟵ aliases: 55310008, Tarjeta Modbus, Modbus Card, Tarjeta de expansión Modbus del sistema convencional, Conventional System Modbus Expansion Cards

## `08895_04-multiling`  [agree]
  identity: brand='Menvier CSA' oem='Menvier Csa Srl'
    [prim/both] **1555**  ⟵ aliases: Art. 1555, Art.1555
    [prim/both] **1555 SS**  ⟵ aliases: Art. 1555 SS, Art.1555 SS
    [prim/both] **5055**  ⟵ aliases: Art. 5055, Art.5055
    [prim/both] **5055 SS**  ⟵ aliases: Art. 5055 SS, Art.5055 SS
    [prim/both] **5555**  ⟵ aliases: Art. 5555, Art.5555
    [prim/both] **5555 SS**  ⟵ aliases: Art. 5555 SS, Art.5555 SS

## `00-3218-501-0000-07_r007_2x-lb_installation_sheet_ml`  [agree]
  identity: brand='Aritech' oem='KGS Manufacturing Poland Sp. z.o.o.'  ⚠ field_conflicts=['brand_on_doc']
    [prim/both] **2X-LB**  ⟵ aliases: 2X-LB Loop Board, 2X-LB Loop Expansion Board, 00-3218-501-0000-07

## `50478 RevA - MPS-24AE _Eng`  [agree]
  identity: brand='Notifier' oem='unknown'
    [prim/both] **MPS-24AE**  ⟵ aliases: 

## `15888SP`  [superset]
  identity: brand='Notifier' oem='Notifier'  ⚠ field_conflicts=['brand_on_doc']
    [prim/both] **BE-XP**  ⟵ aliases: Paquete del Equipo Básico BE-XP, Transpondedor XP, Transpondedor de la Serie XP, El Transpondedor XP
    [prim/both] **CHS-4**  ⟵ aliases: Chasis CHS-4
    [prim/both] **XPC-8**  ⟵ aliases: Módulo de Control del Transpondedor XPC-8, El Módulo XPC-8
    [prim/gpt] **XPDP**  ⟵ aliases: Panel Embellecedor XP, Panel Embellecedor del Transponder XPDP
    [prim/both] **XPM-8**  ⟵ aliases: Módulo de Monitoreo del Transpondedor XPM-8, El Módulo XPM-8
    [prim/both] **XPM-8L**  ⟵ aliases: Módulo de Monitoreo del Transpondedor XPM-8L, El Módulo XPM-8L
    [prim/both] **XPP-1**  ⟵ aliases: Módulo de Proceso del Transpondedor, Procesador XPP-1
    [prim/both] **XPR-8**  ⟵ aliases: El Módulo XPR-8
    [seco/both ⟵split(AVPS-24 y AVPS-24E)] **AVPS-24**  ⟵ aliases: AVPS-24 y AVPS-24E
    [seco/both ⟵split(AVPS-24 y AVPS-24E)] **AVPS-24E**  ⟵ aliases: AVPS-24 y AVPS-24E, La Fuente de Alimentación Audio Visual AVPS-24/AVPS-24E
    [seco/both ⟵split(MPS-24A/MPS-24AE)] **MPS-24A**  ⟵ aliases: 
    [seco/both ⟵split(MPS-24A/MPS-24AE)] **MPS-24AE**  ⟵ aliases: Fuente de Alimentación Principal MPS-24A/MPS-24AE, producto de exportación
    [seco/both ⟵split(MPS-24B/MPS-24BE)] **MPS-24B**  ⟵ aliases: 
    [seco/both ⟵split(MPS-24B/MPS-24BE)] **MPS-24BE**  ⟵ aliases: Fuente de Alimentación Principal MPS-24B/MPS-24BE, producto de exportación
    [seco/both] **XRAM-1**  ⟵ aliases: plaqueta de RAM no volátil XRAM-1, plaqueta RAM no volátil XRAM-1, El XRAM-1
    [seco/gpt ⟂candidate] **APS-6R**  ⟵ aliases: Fuente de Alimentación Auxiliar APS-6R
    [seco/gpt ⟂candidate] **BP-3**  ⟵ aliases: Panel Embellecedor de la Batería BP-3
    [seco/gpt ⟂candidate] **CAB-A3**  ⟵ aliases: CAB-A3 - Gabinete de Hilera Singular
    [seco/gpt ⟂candidate] **CAB-B3**  ⟵ aliases: CAB-B3 - Gabinete de Hilera Doble
    [seco/gpt ⟂candidate] **CAB-C3**  ⟵ aliases: CAB-C3 - Gabinete de Hilera Triple
    [seco/gpt ⟂candidate] **CAB-D3**  ⟵ aliases: CAB-D3 - Gabinete de Hilera Cuádruple, CAB-3 tamaño D
    [seco/gpt ⟂candidate] **CHG-120**  ⟵ aliases: El Cargador de Batería CHG-120, Cargador Remoto de Batería CHG-120
    [seco/gpt ⟂candidate] **CHS-4L**  ⟵ aliases: CHS-4L de bajo perfil, Chasis CHS-4L
    [seco/gpt ⟂candidate] **DP-1**  ⟵ aliases: Panel Embellecedor (DP-1)
    [seco/gpt ⟂candidate] **MPM-2**  ⟵ aliases: Medidor-2 de Energía Principal, Medidor opcional de la Energía Principal
    [seco/gpt ⟂candidate] **MPS-400**  ⟵ aliases: Fuente de Alimentación Principal MPS-400
    [seco/gpt ⟂candidate] **N-ELR**  ⟵ aliases: Placa de Instalación del Resistor N-ELR, Placa de Instalación de Resistor N-ELR
    [seco/gpt ⟂candidate] **NR45-24**  ⟵ aliases: Los Cargadores de Batería Remotos NR45-24 y NR45-24E, Cargador NR45-24
    [seco/gpt ⟂candidate] **NR45-24E**  ⟵ aliases: Los Cargadores de Batería Remotos NR45-24 y NR45-24E
    [seco/gpt ⟂candidate] **VP-2**  ⟵ aliases: Panel Embellecedor Ventilado VP-2

## `HLSI-MA-103-I_GuiaRapida_RP1r-Supra_EN_lr`  [agree]
  identity: brand='Honeywell' oem='unknown'
    [prim/both ⟵split(VSN-RP1r+)] **ESS-RP1r-Supra**  ⟵ aliases: 
    [prim/both ⟵split(VSN-RP1r+)] **RP1r-Supra**  ⟵ aliases: 
    [prim/gpt] **VSN-RP1r+**  ⟵ aliases: 

## `MADT155_08`  [agree]
  identity: brand='Notifier' oem='Honeywell'  ⚠ field_conflicts=['brand_on_doc']
    [prim/both ⟵split(ID50/60)] **ID50**  ⟵ aliases: ID50/60
    [prim/both ⟵split(ID50/60)] **ID60**  ⟵ aliases: 

## `MADT285`  [agree]
  identity: brand='Notifier' oem='unknown'
    [prim/both ⟵split(AM2020/AFP1010)] **AFP1010**  ⟵ aliases: 
    [prim/both ⟵split(AM2020/AFP1010)] **AM2020**  ⟵ aliases: 

## `MCDT156_A`  [agree]
  identity: brand='Notifier' oem='unknown'  ⚠ field_conflicts=['brand_on_doc', 'distributor']
    [prim/both ⟵split(ID50/60)] **ID50**  ⟵ aliases: ID50/60, ID5x/ID6x, ID5x/6x, serie ID5x/ID6x, Centrales ID5x/6x
    [prim/both ⟵split(ID50/60)] **ID60**  ⟵ aliases: ID5x/ID6x, ID5x/6x, serie ID5x/ID6x, Centrales ID5x/6x

## `00-3280-508-4109-06_r006_2x-at_series_quick_start_guide_es`  [agree]
  identity: brand='Kidde' oem='KGS Manufacturing Poland Sp. z.o.o.'  ⚠ field_conflicts=['brand_on_doc']
    [prim/both] **2X-AT-F1-FB-S**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-F2**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-F2-FB**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-F2-FB-P**  ⟵ aliases: serie 2X-AT, variante -P
    [prim/both] **2X-AT-F2-FB-S**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-F2-P**  ⟵ aliases: serie 2X-AT, variante -P
    [prim/both] **2X-AT-F2-S**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-FR**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-FR-FB**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-FR-FB-S**  ⟵ aliases: serie 2X-AT
    [prim/both] **2X-AT-FR-S**  ⟵ aliases: serie 2X-AT

## `085501945t_PA5_Installation_manual_D-GB-F-RU-IT`  [agree]
  identity: brand='PATROL' oem='unknown'
    [prim/both] **PA 5**  ⟵ aliases: PA 5-SSM, PA 5-24V DC, PA 5/ PA X 5, PATROL sounders and combined units PA 5/ PA X 5
    [prim/both] **PA X 5-05**  ⟵ aliases: PA X 5-xx-SSM, PA X 5, PATROL sounders and combined units PA 5/ PA X 5, sounder –beacon combination
    [prim/both] **PA X 5-10**  ⟵ aliases: PA X 5-xx-SSM, PA X 5, PATROL sounders and combined units PA 5/ PA X 5, sounder –beacon combination
    [seco/gpt ⟂candidate] **-SSM**  ⟵ aliases: –SSM, SSM, Soft-Start-Module, PA 5-SSM, PA X 5-xx-SSM

## `15274 RevB - RZA-4X_Eng`  [superset]
  identity: brand='Notifier' oem='Notifier'
    [prim/both] **RZA-4X**  ⟵ aliases: Remote Zone Annunciator Module, RZA-4X Remote Annunciator
    [seco/opus ⟂candidate] **4XLM**  ⟵ aliases: LED Interface Module

## `18500_A4_VESDA_VLI_Product_Guide_A4_IE_lores`  [superset]
  identity: brand='VESDA by Xtralis' oem='Xtralis'
    [prim/both] **VLI-880**  ⟵ aliases: VESDA VLI Standalone, VESDA VLI, VLI detector, VESDA VLI detector, VLI
    [prim/both] **VLI-885**  ⟵ aliases: VESDA VLI with VESDAnet Card, VESDAnet enabled VLI, VESDA VLI, VLI detector, VESDA VLI detector…
    [seco/gpt ⟂candidate] **VRT-Q00**  ⟵ aliases: VESDA VLI Remote Display with RTC7, Remote Display Module, Remote Display unit, Remote Display
    [seco/gpt ⟂candidate] **VRT-T00**  ⟵ aliases: VESDA VLI Remote Display with RTC0, Remote Display Module, Remote Display unit, Remote Display

## `1998M0901_FS24X_ES-AR54-10_ES-AR_RevB_17July2015`  [superset]
  identity: brand='Honeywell' oem='Honeywell Analytics'  ⚠ field_conflicts=['oem_manufacturer']
    [prim/opus] **FS24X**  ⟵ aliases: FS24X-211, FS24X-211-221, Modelo FS24X, FS24X QuadBand Triple IR, Detector de Triple IR QuadBand campo de visión 110°
    [prim/gpt] **FS24X-2**  ⟵ aliases: Modelo FS24X, FS24X QuadBand Triple IR™, FS24X QuadBand, FS24X-211, FS24X-211-221…
    [prim/both] **FS24X-9**  ⟵ aliases: FS24X-911, FS24X-911-211, FS24X-911-24-5, FS24X911-24-5, Detector de Triple IR QuadBand campo de visión 90°…
    [seco/gpt ⟂candidate] **FVR-01**  ⟵ aliases: modelo FVR-01, limitador del campo de visión modelo FVR-01
    [seco/gpt ⟂candidate] **SM4**  ⟵ aliases: modelo SM4, Montaje giratorio SM4
    [seco/gpt ⟂candidate] **TL-1055**  ⟵ aliases: TL1055X, Lámpara de prueba portátil TL-1055 (NEMA 1)
    [seco/gpt ⟂candidate] **TL-2055**  ⟵ aliases: TL2055X, Lámpara de prueba portátil TL-2055 para áreas peligrosas

## `1998M0901_FS24X_PT-BR54-10_PT-BR_RevB_20July2015`  [superset]
  identity: brand='Honeywell' oem='Honeywell Analytics Inc.'
    [prim/both] **FS24X**  ⟵ aliases: 
    [seco/opus ⟂candidate] **SM4**  ⟵ aliases: 