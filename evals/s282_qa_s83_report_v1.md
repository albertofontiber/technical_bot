# s282 QA-s83 — Validacion del activo de identidad s83 para el Tramo 2 — v1

Instrumento: `scripts/s282_qa_s83_instrument.py`. **READ-ONLY (PostgREST GET), SELECT-only, 0 escrituras, 0 embeddings de pago.** Valida, por cada uno de los 1014 `source_file` del activo s83, si sus etiquetas (`product_model`/`language`/`doc_type`) son APLICABLES a la DB con confianza medible, fusionando 3 fuentes de evidencia (doc-level DB + s83 + catalogo; +contenido para el juez). La derivacion determinista es $0 y 2x byte-identica; el juez LLM (`claude-haiku-4-5`, temp 0) arbitra SOLO el subconjunto WEAK.

## Freeze-contract

- commit HEAD: `f1bee301269a336ccfa36ab432d9d6a6e62fd250` (worktree dirty: True)
- corpus fingerprint: chunks_v2=25090 · documents=1171 · sha256 `aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d`
- **determinismo 2x: IDENTICO** (pass1 `2cbaa80d571f35a4` == pass2 `2cbaa80d571f35a4`)
- s83 modelos: sha256-LF `a1291a837a7f905c3a7939cd847675a94811a47073fa12143070c0f61b177b19` · s83 identidad `87bc0db79ead4e126a388f425049d5029dda9bc64920a0e8f8dca87b8ce6168a` · doc_map `67cb2b66dd2ccf9cd7bc2f84d0b2d06b8eaf84b8db77533aa07fa76cebae5161`
- generado 2026-07-24T06:45:05.672892+00:00

## 1. Titular — distribucion de veredictos (de 1014 source_files s83)

La derivacion DETERMINISTA ($0, recall-safe) solo emite AUTO_CLEAN (corroboracion exacta/subset de la etiqueta gobernada por los propios modelos s83), WEAK (todo lo no-obvio) y UNMAPPED. El CONFLICT es una salida del JUEZ LLM sobre contenido — un pm string-disjunto no basta para declarar conflicto (puede ser familia/variante, ruido de filename, o descripcion generica).

| veredicto DETERMINISTA | n | % |
|---|---:|---:|
| **AUTO_CLEAN** | 443 | 43.7% |
| **WEAK** | 555 | 54.7% |
| **UNMAPPED** | 16 | 1.6% |

Relacion determinista del pm (por que cada fila cae donde cae): `{'corroborated': 445, 'disjoint': 60, 'doc_noise': 311, 'family': 130, 'no-active-doc': 16, 's83_empty': 22, 's83_generic': 30}`.

**Juez LLM (`claude-haiku-4-5`, temp 0) sobre el subconjunto WEAK** — 555/555 juzgados: AUTO_CLEAN=436 · CONFLICT=89 · WEAK=30. **Coste real: $0.8876** (607543 in / 56020 out tok, 535 llamadas nuevas de API).

| veredicto FINAL (det + LLM) | n | % |
|---|---:|---:|
| **AUTO_CLEAN** | 879 | 86.7% |
| **CONFLICT** | 89 | 8.8% |
| **WEAK** | 30 | 3.0% |
| **UNMAPPED** | 16 | 1.6% |

**Estimacion T2 desbloqueado:** **879** source_files aplicables tal cual (AUTO_CLEAN det + LLM), **89** conflictos para Alberto, 30 WEAK residuales.

## 2. Distribucion por marca (veredicto FINAL x marca DB)

| marca | AUTO_CLEAN | CONFLICT | WEAK | UNMAPPED | total |
|---|---:|---:|---:|---:|---:|
| Notifier | 406 | 48 | 13 | 0 | 467 |
| Morley | 195 | 30 | 11 | 0 | 236 |
| Detnov | 58 | 0 | 1 | 0 | 59 |
| Aritech | 49 | 0 | 0 | 0 | 49 |
| Kidde | 34 | 0 | 1 | 0 | 35 |
| System Sensor | 30 | 0 | 0 | 0 | 30 |
| Xtralis | 21 | 4 | 3 | 0 | 28 |
| Spectrex | 17 | 0 | 0 | 0 | 17 |
| (sin marca) | 0 | 0 | 0 | 16 | 16 |
| Pfannenberg | 10 | 3 | 0 | 0 | 13 |
| Argus Security | 12 | 0 | 0 | 0 | 12 |
| LDA audioTech | 11 | 0 | 0 | 0 | 11 |
| Securiton | 8 | 0 | 0 | 0 | 8 |
| Fidegas | 6 | 0 | 0 | 0 | 6 |
| Honeywell | 3 | 0 | 0 | 0 | 3 |
| Sensitron | 3 | 0 | 0 | 0 | 3 |
| Edwards | 2 | 1 | 0 | 0 | 3 |
| Pepperl-Fuchs | 3 | 0 | 0 | 0 | 3 |
| LGM Products | 2 | 0 | 0 | 0 | 2 |
| Avotec | 2 | 0 | 0 | 0 | 2 |
| FUEGO | 1 | 0 | 0 | 0 | 1 |
| COELBO | 1 | 0 | 0 | 0 | 1 |
| Hosiden Besson | 1 | 0 | 0 | 0 | 1 |
| KAC | 1 | 0 | 0 | 0 | 1 |
| Sound Alert | 0 | 1 | 0 | 0 | 1 |
| European Safety Systems | 0 | 1 | 0 | 0 | 1 |
| Venitem | 1 | 0 | 0 | 0 | 1 |
| Zellweger Analytics | 1 | 0 | 0 | 0 | 1 |
| SenseWare | 0 | 1 | 0 | 0 | 1 |
| OGGIONI | 1 | 0 | 0 | 0 | 1 |
| Testifire | 0 | 0 | 1 | 0 | 1 |

## 3. Packet de CONFLICTOS para Alberto (89) — hallados por el juez sobre contenido

Cada fila: s83 propone X, pero el CONTENIDO del documento y/o la etiqueta gobernada indican otro producto — el juez LLM lo declaro CONFLICT leyendo las primeras paginas. Patron del caso FS2-1 del packet T3. Alberto adjudica cual gobierna el T2. (Nada se aplica; el re-tag/backfill es reversible.)

| source_file | s83 primarios | doc-level pm (DB) | el juez dice | motivo (LLM) |
|---|---|---|---|---|
| `04-4001-501-2009-12_r012_modulaser_en_` | ['Módulo de detector', 'Módulo de visualización de comandos', 'Módulo de visualización estándar'] | `FHSD8310` | `ModuLaser` | El documento describe específicamente el detector ModuLaser (aspiración modular), mientras |
| `15090SP` | ['NRT-586T'] | `15090SP` | `15090SP` | El contenido menciona 'Terminal de Informe de Red' (Network Report Terminal), identificand |
| `37430_00_FAAST_FLEX_Bluetooth_User_Gui` | ['Honeywell SmartConfig App'] | `FAAST FLEX` | `FAAST FLEX` | s83 propone 'Honeywell SmartConfig App' pero el documento es claramente una guía de usuari |
| `37444_A1_Xtralis_Li-ion_Tamer_GEN3_Use` | ['LT-ACC-HUB-POE', 'LT-ACC-HUB-PWR', 'LT-CTR-SML'] | `Li-ion Tamer GEN3` | `Li-ion Tamer GEN3` | El contenido del documento claramente documenta 'Li-ion Tamer GEN3' (producto principal),  |
| `4188-1124-ES issue 6_01-2026_To` | ['E10', 'E15'] | `INSPIRE` | `INSPIRE` | El contenido describe claramente la Central INSPIRE de Notifier y su programa de configura |
| `ASD Harsh Environments_SP` | [] | `ASD` | `FAAST` | El contenido claramente documenta FAAST (Fire Alarm Aspiration Sensing Technology), no ASD |
| `Al cambiar-el-nombre-del-plano-a desap` | [] | `unknown` | `unknown` | s83 propone Honeywell pero DB indica Morley. Contenido es un Q&A técnico sobre software TG |
| `Como-solucionar-la-incidencia-TABLE-IS` | [] | `unknown` | `unknown` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'TG' (software gráfico) si |
| `Con-que-Sistema-Operativo-es-compatibl` | [] | `unknown` | `Morley ZX/DX` | s83 propone Honeywell pero DB y contenido indican Morley. El documento trata sobre compati |
| `Conexionado-del-modulo-M710-CZ-MI-DCZM` | ['M710-CZ', 'MI-DCZM'] | `ID3000` | `M710-CZ / MI-DCZM` | El contenido del documento claramente documenta M710-CZ y MI-DCZM, pero la etiqueta gobern |
| `Conexionado-del-modulo-M710-CZR-MI-DCZ` | ['M710-CZR', 'MI-DCZRM'] | `ID3000` | `M710-CZR / MI-DCZRM` | El contenido del documento claramente documenta M710-CZR/MI-DCZRM (título y contenido expl |
| `Conexionado-del-modulo-M710-MI-DMMI` | ['M710', 'MI-DMMI'] | `ID3000` | `ID3000` | Etiqueta gobernada indica ID3000 (Notifier), pero s83 propone M710/MI-DMMI (Morley). Conte |
| `D 1101-7 Sounder Beacon` | ['CWSS-xx-S5', 'CWSS-xx-S6', 'CWSS-xx-W5'] | `D1101` | `CWSS-xx-S5, CWSS-xx-S6, CWSS-xx-W5, CWSS-xx-W6` | El contenido claramente documenta modelos CWSS-xx (ENScape Sounder Beacon), pero la etique |
| `D 1147-1 BRH Notifier` | ['BRH'] | `B501AP` | `B501AP` | El contenido menciona explícitamente 'B501' (modelo B501AP gobernado en DB), mientras que  |
| `D 1148-1 BRS Notifier` | ['NFXI-BSF-WCS'] | `B501AP` | `B501AP` | El contenido menciona explícitamente 'NFXI-BSF-WCS' en secciones técnicas (conexiones, dim |
| `D700-3-Eng` | ['MCP1A', 'MCP1B', 'MCP2A'] | `D700` | `MCP1A, MCP1B, MCP2A, MCP2B, MCP3A, MCP4A` | Content clearly documents MCP series manual call points (MCP1A, MCP2A, MCP3A, MCP4A). DB l |
| `D700-3-Sp` | ['MCP1A', 'MCP1B', 'MCP2A'] | `D700` | `MCP1A, MCP1B, MCP2A, MCP2B, MCP3A, MCP4A` | El contenido claramente documenta pulsadores manuales MCP (MCP1, MCP2, MCP3, MCP4), pero l |
| `D838-1_kac sounders` | [] | `D838` | `D838` | s83 propone System Sensor pero DB y filename indican Notifier D838. Contenido técnico (dim |
| `DXC-Referencias-repuestos` | [] | `unknown` | `DXC` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'DXC' (producto Morley), n |
| `DXc-Conexion-Como-solucionar-la-averia` | [] | `unknown` | `DXc/Conexion` | s83 propone Honeywell pero DB indica Morley. Contenido menciona explícitamente 'DXc/Conexi |
| `DXc-Connexion-Como-solucionar-la-averi` | [] | `unknown` | `DXc/Connexion` | s83 propone Honeywell pero DB y contenido indican Morley DXc/Connexion. Fabricantes distin |
| `DXc-Opciones-de-disparo-de-programas-M` | [] | `unknown` | `DXc` | s83 propone Honeywell pero DB y contenido indican Morley DXc. Marca fabricante claramente  |
| `DXc-Tipos-Abreviaturas-de-equipos` | [] | `unknown` | `DXc` | s83 propone Honeywell pero DB indica Morley. Contenido documenta 'DXc' (central/sistema Mo |
| `Datasheet-CAD-171-DS-737-en` | ['CAD-171'] | `DS-737` | `CAD-171` | El contenido del documento describe claramente el CAD-171 (panel de control direccionable  |
| `Datasheet_CAD-171-DS-736-es` | ['CAD-171'] | `DS-736` | `CAD-171` | El contenido del documento claramente documenta el CAD-171 (Sistema Analógico, Serie VESTA |
| `ExitPoint- WP ENG` | [] | `ExitPoint` | `Directional Sound` | s83 propone System Sensor pero DB indica Sound Alert. Contenido menciona 'Directional Soun |
| `F5K-2H-UserGuide-SPANISH_Manual F5000` | ['F5K-2H'] | `F5000` | `F5000` | La etiqueta gobernada indica F5000 (Morley). El contenido describe un detector de humos co |
| `F5K-Additional-Information-Spanish` | ['F5K'] | `F5000` | `F5000` | La etiqueta gobernada indica F5000 (Morley), pero s83 propone F5K. El contenido describe u |
| `GT-HLSI-1102 ITAC 2_1  25-02-2025 v4` | ['ITAC 2.0'] | `AM-8200` | `ITAC 2.0` | El contenido documenta claramente ITAC 2.0 (pasarela de comunicación). La etiqueta goberna |
| `HLSI-MN-627` | ['KIT-GAS'] | `SMART 3` | `SMART 3` | El contenido claramente documenta el SMART 3 (detector de gas y su teclado de calibración) |
| `HLSI-TI-005` | [] | `RP1r` | `RP1r` | El contenido claramente documenta la serie RP1r (centrales de extinción RP1r), mientras qu |
| `HLSI-TI-007_VSN-4REL` | [] | `VSN-4REL` | `VSN-4REL` | Documento de Honeywell Life Safety Iberia pero etiqueta gobernada asigna manufacturer Morl |
| `HLSI_MA102_bis2` | [] | `unknown` | `Morley Central de Extinción` | s83 propone Honeywell Life Safety Iberia pero DB y contenido indican Morley. Documento des |
| `HSLI_IN_020_Tabla equivalencia TG` | [] | `RP1R` | `unknown` | s83 propone Honeywell sin modelo específico, pero DB indica RP1R (Xtralis). Contenido es t |
| `I56-0790-003_CPX-751E` | ['CPX-751E'] | `B501` | `CPX-751E` | El contenido del documento describe explícitamente el modelo CPX-751E (título, especificac |
| `I56-1291-002_FDX-551REM Manual` | ['FDX-551REM'] | `B501` | `FDX-551REM` | El contenido del documento claramente documenta el modelo FDX-551REM (aparece explícitamen |
| `I56-1292-002_FDX-551HTEM Manual` | ['FDX-551HTEM'] | `B501` | `FDX-551HTEM` | El contenido del documento claramente documenta el modelo FDX-551HTEM (aparece explícitame |
| `I56-1320-001 SDX-751TEM` | ['SDX-751TEM'] | `B501` | `SDX-751TEM` | El contenido del documento describe explícitamente el modelo SDX-751TEM (título, instrucci |
| `I56-1641-002_FDX-551EM Manual` | ['FDX-551EM'] | `B501` | `FDX-551EM` | El contenido del documento claramente documenta el modelo FDX-551EM (aparece explícitament |
| `I56-1657-001 MI-PTSE` | ['MI-PTSE'] | `DE-15` | `MI-PTSE` | El contenido del documento claramente documenta el modelo MI-PTSE (título, instrucciones e |
| `I56-2129-002 M710-CZ` | ['M710-CZ'] | `MIN-17` | `M710-CZ` | El contenido claramente documenta M710-CZ (título, especificaciones, instalación). La etiq |
| `I56-4208-001 NRX-REP Repeater Web` | ['NRX-REP'] | `B501RF` | `B501RF` | El contenido del documento identifica claramente el modelo B501RF (visible en especificaci |
| `IS5001-F_IS-mA1_EN` | ['IS-mA1'] | `IS5001` | `IS-mA1` | El contenido claramente documenta IS-mA1 (título, certificado ATEX, especificaciones). La  |
| `ITAC-no-reconocido-por-la-Central` | ['ITAC'] | `ID3000` | `ID3000` | s83 propone ITAC genérico, pero DB y contenido indican ID3000 (Notifier). El documento tra |
| `Instrucciones_PUL-VSN_MULTI` | ['PA-RZ1'] | `PUL-VSN` | `MIE-MI-150` | El contenido describe claramente el modelo MIE-MI-150 (pulsador de alarma manual convencio |
| `MADT155_02` | ['ID60'] | `ID50` | `ID50` | El contenido claramente indica que es un ANEXO de los Manuales de la central ID50 (versión |
| `MADT190_01` | ['ISO-IDRED/W'] | `ID2net` | `ID2net` | El contenido del documento claramente identifica 'ID²net' como el producto documentado (tí |
| `MADT190_05` | ['NGU'] | `ID3000` | `NGU` | El documento trata sobre el módulo NGU (Ref. 002-467) para la central ID3000. S83 propone  |
| `MADT190_10` | ['020-590', '020-591', '020-592'] | `ID3000` | `020-590, 020-591, 020-592, 020-593, 020-594, 020-595, 020-596, 020-598, 020-606` | El documento es un manual de montaje de Rack 19" que cubre múltiples kits específicos (020 |
| `MADT190_15` | ['PSU7A'] | `ID3000` | `PSU7A` | El contenido claramente documenta PSU7A (título, procedimientos, fusibles específicos). La |
| `MADT232` | ['AFP4000'] | `MA-DT-232` | `MA-DT-232` | El contenido menciona explícitamente 'Central AFP4000' pero el documento MA-DT-232 es un m |
| `MADT282` | ['IC-485S'] | `DIA (DIB)` | `DIA (DIB)` | El contenido describe claramente 'Convertidores RS-232/RS-485' para la tarjeta interface D |
| `MADT370` | ['INA', 'MIB-F', 'MIB-W'] | `NOTI-FIRE-NET` | `NOTI-FIRE-NET (sistema completo de red)` | El contenido documenta el sistema NOTI-FIRE-NET completo (NRT, MIB, SIB-NET, AM2020, AFP10 |
| `MADT951_01` | ['AFP1010', 'AFP400', 'AM2020'] | `TG-NOTIFIER` | `TG (programa gráfico)` | El documento es un manual de conexión del programa gráfico TG con centrales NOTIFIER (ID50 |
| `MIDT1450` | ['FKAC2100R', 'FLG2100', 'FRM2100'] | `ID3000` | `FRM2100, FDKM2100X, FKAC2100R, FLG2100` | El contenido documenta explícitamente FRM2100, FDKM2100X, FKAC2100R y FLG2100. La etiqueta |
| `MIDT340` | ['AA-100', 'AA-100E', 'AA-120'] | `MI-DT-340` | `AM2020/AFP1010` | El contenido describe claramente 'Sistema de Megafonía y Telefonía en las Centrales AM2020 |
| `MIE-MI-330` | ['RS-232'] | `Comunicador MIE-330` | `RS-232` | El contenido claramente documenta la tarjeta RS-232 (MOD.RS-232), no el Comunicador MIE-33 |
| `MIW-al-sustituir-las-baterias-de-un-eq` | [] | `unknown` | `Morley` | S83 propone Honeywell pero DB gobernada indica Morley como fabricante. Contenido es genéri |
| `MNDT285` | ['UPDL-1020', 'VeriFire-1020'] | `AM2020/AFP1010` | `AM2020/AFP1010` | El contenido claramente documenta el sistema AM2020/AFP1010 (mencionado explícitamente en  |
| `MNDT410` | ['ACM-16AT', 'ACM-32A', 'AEM-16AT'] | `DT-410` | `ACS (ACM-16AT, ACM-32A, ABM-16AT, ABM-32A, ABF-1, ABF-2, ABF-4, ABS-1, ABS-2)` | El documento es sobre la Serie ACS (anunciadores y módulos de control). La etiqueta gobern |
| `MNDT600` | [] | `VGS` | `MN-DT-600` | El documento es un manual de usuario/mantenimiento para detectores de gas MN-DT-600 (Notif |
| `MNDT618` | ['S313HSAP', 'S319HSAP'] | `S313HSAP and S319HSAP` | `SENSITRON SMART 2` | El contenido describe detectores SENSITRON SMART 2 para sulfuro de hidrógeno, no modelos S |
| `MNDT630` | ['STS3REL'] | `SMART3` | `STS3REL` | El contenido claramente documenta STS3REL (tarjeta de relé), pero la etiqueta gobernada en |
| `MNDT651` | ['S540(539) CODP', 'S540(539) COSP'] | `PARK` | `PARK` | El contenido claramente identifica el producto como 'PARK' (detector de monóxido de carbon |
| `MNDT690` | ['20/20-I', '20/20-L', '20/20-LB'] | `MN-DT-690` | `SharpEye 20/20U` | El contenido menciona explícitamente 'SharpEye 20/20U / 752002' como detector de llama UV. |
| `OSID-Es-necesario-resetear-la-barrera-` | [] | `unknown` | `Morley OSID` | S83 propone Honeywell pero DB y contenido indican Morley. Documento trata sobre barrera OS |
| `Poner-la-contraseña-por-defecto-del-pr` | [] | `unknown` | `unknown` | s83 propone Notifier pero DB indica Morley. Contenido trata software gráfico TG genérico s |
| `Rearme-remoto-en-central-DXc-Connexion` | ['DX-Connexion'] | `CZ6` | `MI-CZ6` | El contenido menciona explícitamente 'MI-CZ6' (módulo de zona) como elemento principal, co |
| `Requisitos-del-PC-para-el-TG-Version-5` | [] | `unknown` | `TG` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'TG Versión 5.XX' (product |
| `SFD-220_Manual_EN` | ['VTB-32E'] | `DS109F` | `VTB-32E` | Content clearly documents VTB-32E (Cranford Controls), but DB governs DS109F (Pfannenberg) |
| `SW_MN_210-Series_CZ_flame_detectors_v1` | ['IR3-109/1CZ', 'UV-185/5CZ', 'UV/IR-210/1CZ'] | `210-SERIES` | `UV-185/5CZ, UV/IR-210/1CZ, IR3-109/1CZ` | El contenido documenta explícitamente tres modelos específicos (UV-185/5CZ, UV/IR-210/1CZ, |
| `Solicitud-asistencia-curso-de-formacio` | [] | `unknown` | `unknown` | s83 propone Honeywell Life Safety pero DB indica Morley (fabricante distinto). Contenido e |
| `TG-ATENCION-El-sistema-no-encuentra-la` | [] | `unknown` | `unknown` | s83 propone Honeywell pero DB indica Morley. Contenido es genérico (ticket de soporte TG s |
| `TG-Como ampliar-licencias` | [] | `unknown` | `TG` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'TG' (producto Morley), no |
| `TG-Como-borrar-elementos-de-un-plano` | [] | `unknown` | `unknown` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'TG' (versión 7) sin ident |
| `TG-Como-cargar-añadir-planos` | [] | `unknown` | `Morley` | s83 propone Honeywell pero DB y contenido indican Morley. Documento es guía de software TG |
| `TG-Como-hacer-una-copia-de-seguridad-d` | [] | `unknown` | `unknown` | s83 propone Honeywell pero DB indica Morley. Contenido es genérico (backup de proyecto TG  |
| `TG-Como-puedo-ver-los-equipos-que-no-e` | [] | `unknown` | `Morley TG` | S83 propone Honeywell pero DB y contenido indican Morley TG. Conflicto claro de fabricante |
| `TG-Como-reparar-Historico-Provisional` | [] | `unknown` | `Honeywell TG` | El contenido menciona explícitamente 'Honeywell\BD_TG' y es un documento de soporte técnic |
| `TG-SE-HA-SUPERADO-EL-MAXIMO-DE-LICENCI` | [] | `unknown` | `Morley` | s83 propone Honeywell pero DB y contenido indican Morley. El documento trata sobre licenci |
| `TG-como-se-configuran-sonidos-ante-eve` | [] | `unknown` | `TG` | s83 propone Honeywell pero DB indica Morley. Contenido menciona 'TG' (producto Morley), no |
| `TIDT066_copia` | [] | `ID3000` | `ID1000` | El contenido describe claramente la central ID1000 (no ID3000). El título menciona 'INCOMP |
| `TIDT089` | ['AIS-GALD1', 'AIS-GALS1', 'Y72221'] | `ID3000` | `Z978, AIS-GALD1, AIS-GALS1` | El contenido menciona explícitamente 'barreras Zener Z978' y 'aisladores galvánicos' (AIS- |
| `TIDT089_copia` | ['AIS-GALD1', 'AIS-GALS1', 'Y72221'] | `ID3000` | `AIS-GALD1, AIS-GALS1, Z978` | Contenido documenta aisladores galvánicos y barreras Zener (Z978) para equipos NOTIFIER EX |
| `TIDT105` | ['777163'] | `S40/40` | `S40/40` | El contenido claramente describe un protector de intemperie para detectores S40/40, no el  |
| `UCIP-Como hacer una Actualizacion` | ['UCIP'] | `ID3000` | `ID3000` | El contenido menciona explícitamente 'centrales ID50/ID3000', indicando que el documento t |
| `UCIP-Como-conectar-con-TG` | ['UCIP'] | `ID3000` | `ID3000` | s83 propone UCIP genérico, pero la etiqueta gobernada en DB indica ID3000 específico. El c |
| `UCIP-Compatibilidades-con-centrales-ac` | ['UCIP'] | `ID60` | `ID60` | DB etiqueta el documento como ID60 (Notifier), pero s83 propone UCIP (Honeywell). El conte |
| `VGS TOXICOS _SP rev 1` | ['VGS DU', 'VGS-AD'] | `VGS-TOXICOS` | `VGS-TOXICOS` | La etiqueta gobernada indica VGS-TOXICOS (detector de gas tóxico), pero s83 propone VGS DU |

### 3b. (Transparencia) Candidatos deterministas pm-DISJUNTO (60)

El heuristico de strings marco estos como pm-disjunto; el juez LLM los reclasifica leyendo contenido (muchos son familia/variante o ruido de filename, NO conflictos). Se listan para que el packet sea auditable.

| source_file | s83 primarios | doc-level pm | veredicto final |
|---|---|---|---|
| `15037SP` | ['LCD-80'] | `AM2020/AFP1010` | AUTO_CLEAN |
| `15090SP` | ['NRT-586T'] | `15090SP` | CONFLICT |
| `15584` | ['CPU-5000'] | `Systema 5000` | AUTO_CLEAN |
| `33976_13_VESDA-E_VEP-A00-P_Product_Gui` | ['VEP-A00-1P', 'VEP-A00-P'] | `VESDA-E VEP-A00` | AUTO_CLEAN |
| `37444_A1_Xtralis_Li-ion_Tamer_GEN3_Use` | ['LT-ACC-HUB-POE', 'LT-ACC-HUB-PWR', 'LT-CTR-SML'] | `Li-ion Tamer GEN3` | CONFLICT |
| `BTDT076` | ['ISO-RS232'] | `ID3000` | AUTO_CLEAN |
| `Conexionado-del-modulo-M710-CZ-MI-DCZM` | ['M710-CZ', 'MI-DCZM'] | `ID3000` | CONFLICT |
| `Conexionado-del-modulo-M710-CZR-MI-DCZ` | ['M710-CZR', 'MI-DCZRM'] | `ID3000` | CONFLICT |
| `Conexionado-del-modulo-M710-MI-DMMI` | ['M710', 'MI-DMMI'] | `ID3000` | CONFLICT |
| `D 1101-7 Sounder Beacon` | ['CWSS-xx-S5', 'CWSS-xx-S6', 'CWSS-xx-W5'] | `D1101` | CONFLICT |
| `D 1129-1` | ['MCP3A'] | `D1129` | AUTO_CLEAN |
| `D700-3-Eng` | ['MCP1A', 'MCP1B', 'MCP2A'] | `D700` | CONFLICT |
| `D700-3-Sp` | ['MCP1A', 'MCP1B', 'MCP2A'] | `D700` | CONFLICT |
| `Datasheet-CAD-171-DS-737-en` | ['CAD-171'] | `DS-737` | CONFLICT |
| `Datasheet_CAD-171-DS-736-es` | ['CAD-171'] | `DS-736` | CONFLICT |
| `Datasheet_CAD-201-DS-740-es` | ['CAD-201', 'CAD-201-PLUS'] | `DS-740` | AUTO_CLEAN |
| `Datasheet_CAD-201-DS-741-en` | ['CAD-201', 'CAD-201-PLUS'] | `DS-741` | AUTO_CLEAN |
| `F5K-2H-UserGuide-SPANISH_Manual F5000` | ['F5K-2H'] | `F5000` | CONFLICT |
| `F5K-Additional-Information-Spanish` | ['F5K'] | `F5000` | CONFLICT |
| `GT-HLSI-1102 ITAC 2_1  25-02-2025 v4` | ['ITAC 2.0'] | `AM-8200` | CONFLICT |
| `HLSI-TI-005` | [] | `RP1r` | CONFLICT |
| `HONEYWELL-H-GTW-ESP-2.26 Integracion` | ['H-GTW-1', 'H-GTW-N'] | `AM8200` | AUTO_CLEAN |
| `I56-0790-003_CPX-751E` | ['CPX-751E'] | `B501` | CONFLICT |
| `I56-1291-002_FDX-551REM Manual` | ['FDX-551REM'] | `B501` | CONFLICT |
| `I56-1292-002_FDX-551HTEM Manual` | ['FDX-551HTEM'] | `B501` | CONFLICT |
| `I56-1320-001 SDX-751TEM` | ['SDX-751TEM'] | `B501` | CONFLICT |
| `I56-1641-002_FDX-551EM Manual` | ['FDX-551EM'] | `B501` | CONFLICT |
| `I56-1749-020 ECO1000BREL12L_12NL_24L` | ['BREL12L', 'BREL12NL', 'BREL24L'] | `ECO1000 BREL` | AUTO_CLEAN |
| `I56-2129-002 M710-CZ` | ['M710-CZ'] | `MIN-17` | CONFLICT |
| `I56-2955-000_prelim` | ['MI-CR6'] | `M200E` | AUTO_CLEAN |
| `I56-2961-000R` | ['PF24V'] | `D690-06-00` | AUTO_CLEAN |
| `IS5001-F_IS-mA1_EN` | ['IS-mA1'] | `IS5001` | CONFLICT |
| `MADT155_02` | ['ID60'] | `ID50` | CONFLICT |
| `MADT190_02` | ['ISO-RS232'] | `ID3000` | AUTO_CLEAN |
| `MADT190_15` | ['PSU7A'] | `ID3000` | CONFLICT |
| `MADT212` | ['124-065-XXX'] | `ID1000` | AUTO_CLEAN |
| `MADT232` | ['AFP4000'] | `MA-DT-232` | CONFLICT |
| `MADT608` | ['EEV(2)'] | `MA-DT-608` | AUTO_CLEAN |
| `MIDT1450` | ['FKAC2100R', 'FLG2100', 'FRM2100'] | `ID3000` | CONFLICT |
| `MIDT1500_A` | ['IDP-LB1'] | `MI-DT-1500` | AUTO_CLEAN |
| … +20 mas | | | |

## 4. (Advisory) Discrepancias de IDIOMA — DB vs s83 (66)

Ortogonal al `product_model`: el `language` a nivel-documento en DB discrepa de s83. En la muestra dominan docs FAQ/soporte con `language` DB = 'en'/'de' pero contenido y s83 = 'es' → **s83 probablemente CORRIGE el idioma** (util para el T2). Alberto decide; no fuerza el veredicto pm.

| source_file | idioma DB | idioma s83 | doc-level pm |
|---|---|---|---|
| `Averia-de-resistencia-de-baterias-en-central` | ['en'] | ['es'] | `unknown` |
| `Como-configurar-correos-en-un-TG-HONEYWELL` | ['en'] | ['es'] | `TG-HONEYWELL` |
| `Como-solucionar-la-incidencia-TABLE-IS-FULL-` | ['en'] | ['es'] | `unknown` |
| `Compatibilidad-detectores-de-monoxido-NCO10-` | ['de'] | ['es'] | `unknown` |
| `Compatibilidad-entre-equipos-Notifier-y-Morl` | ['en'] | ['es'] | `unknown` |
| `Configuracion-entrada-digital-de-la-central-` | ['en'] | ['es'] | `NFS-Supra` |
| `DXC-Como-conectar-una-sirena-de-lazo` | ['de'] | ['es'] | `B501AP` |
| `DXC-Connexion-Como-programar-una-salida-de-a` | ['de'] | ['es'] | `unknown` |
| `DXC-Connexion-Compatibilidad-de-programas-co` | ['de'] | ['es'] | `unknown` |
| `DXC-Connexion-Instalacion-y-configuracion-de` | ['de'] | ['es'] | `unknown` |
| `DXC-Porque-al-activan-elementos-en-alarma-no` | ['en'] | ['es'] | `unknown` |
| `DXC-Puedo-anular-la-clave-de-usuario-y-acced` | ['de'] | ['es'] | `unknown` |
| `DXC-puedo-cambiar-la-clave-de-nivel-3` | ['de'] | ['es'] | `unknown` |
| `DXc-Configuracion-de-la-tarjeta-232-aislada-` | ['de'] | ['es'] | `unknown` |
| `DXc-Connexion-Como-solucionar-la-averia-de-E` | ['de'] | ['es'] | `unknown` |
| `DXc-Opciones-de-disparo-de-programas-Matrice` | ['de'] | ['es'] | `unknown` |
| `DXc-Tipos-Abreviaturas-de-equipos` | ['de'] | ['es'] | `unknown` |
| `DXc-Tipos-de-accion-para-entradas` | ['en'] | ['es'] | `unknown` |
| `DXc_Connexion Averia-de-resistencia-de-bater` | ['de'] | ['es'] | `unknown` |
| `Eventos-Averias-de-Equipos-en-DXc` | ['en'] | ['es'] | `unknown` |
| `Fallo-I2C-en-RP1rSupra` | ['en'] | ['es'] | `RP1R` |
| `Finales-de-linea-de-las-centrales-convencion` | ['de'] | ['es'] | `NFS2-8` |
| `ITAC-Como-asignar-la-direccion-en-el-ITAC` | ['en'] | ['es'] | `unknown` |
| `ITAC-no-reconocido-por-la-Central` | ['pt'] | ['es'] | `ID3000` |
| `MIW-INT-Asignar-de-direccion-pasarela-detect` | ['de'] | ['es'] | `unknown` |
| `MIW-INT-Averia-de-TAMPER` | ['de'] | ['es'] | `unknown` |
| `MIW-INT-Dar-de-alta-un-detector` | ['de'] | ['es'] | `unknown` |
| `MIW-INT-La-central-indica-averia-de-datos-de` | ['de'] | ['es'] | `unknown` |
| `MIW-INT-Mensaje-de-error-LOEr-via-radio-Morl` | ['de'] | ['es'] | `unknown` |
| `MIW-al-sustituir-las-baterias-de-un-equipo-s` | ['de'] | ['es'] | `unknown` |
| … +36 mas | | | |

## 5. (Advisory) Revisiones de MARCA — DB vs s83 brand/oem (335)

El sello OEM/brand/distribuidor (s55/s78) hace ruido; una discrepancia marca-DB vs s83 se marca `review`, NO fuerza conflicto. Se listan solo los primeros para inspeccion.

| source_file | marca DB | s83 brand_on_doc | s83 oem |
|---|---|---|---|
| `00-3280-501-4003-05_r005_2x-a_series_ins` | Aritech | Kidde Commercial | KGS Manufacturing Poland Sp. z.o.o. |
| `00-3280-501-4009-05_r005_2x-a_series_ins` | Aritech | Kidde Commercial | KGS Manufacturing Poland Sp. z.o.o. |
| `00-3280-505-4009-04_r004_2x-a_series_ope` | Aritech | Kidde Commercial | KGS Manufacturing Poland Sp. z.o.o. |
| `00-3280-507-4003-03_r003_2x-a_series_qui` | Aritech | Kidde Commercial | unknown |
| `00-3280-507-4009-03_r003_2x-a_series_qui` | Aritech | Kidde Commercial | unknown |
| `00-3280-508-4009-03_r003_2x-a_series_qui` | Aritech | Kidde Commercial | unknown |
| `00-3280-508-4109-06_r006_2x-at_series_qu` | Aritech | Kidde | KGS Manufacturing Poland Sp. z.o.o. |
| `00-3280-508-4209-02_r002_2x-at_series_qu` | Aritech | Kidde Commercial | unknown |
| `00-3301-501-4000-04_r004_2x-a-lb_loop_bo` | Aritech | Kidde Commercial | KGS Manufacturing Poland Sp. Z.o.o. |
| `00-3301-501-4100-04_r004_2010-2a-pak-hpl` | Aritech | Kidde Commercial | KGS Manufacturing Poland Sp. z.o.o. |
| `0044-033-01 Guia F5000` | Morley | Fire Fighting Enterprises | Fire Fighting Enterprises Ltd |
| `03-0210-501-4301-02_r002_n-mc_series_mcp` | Aritech | Kidde Commercial | KGS Safety System (Hebei) Co. Ltd. |
| `03-0211-501-3000-05_r005_nc_series_conve` | Aritech | Kidde Commercial | KGS Safety System (Hebei) Co., Ltd. |
| `085501821n_DS10_Installation_manual_D-GB` | Pfannenberg | unknown | unknown |
| `085501945t_PA5_Installation_manual_D-GB-` | Pfannenberg | PATROL | unknown |
| `085501946s_PA20_Installation-manual_D-GB` | Pfannenberg | PATROL | unknown |
| `085501949p_PY X-S-05_Installation_manual` | Pfannenberg | PYRA | unknown |
| `085501987j_PY X-M-05_10_Installation_man` | Pfannenberg | PYRA | unknown |
| `08895_04-multiling` | Notifier | Menvier CSA | Menvier Csa Srl |
| `12484_Ezsense_Ops Manual_EN` | Notifier | Honeywell | Honeywell Analytics |
| … +315 mas | | | |

## 6. Que aplica al Tramo 2 (y que NO)

- **AUTO_CLEAN** → el `language`/`doc_type`/`product_model` de s83 se puede poblar en `documents` sin adjudicacion humana: el doc-level `product_model` ya esta corroborado por los propios modelos s83, y s83 rellena `language`/`doc_type` que hoy son NULL en la mayoria (census: language NULL=902, doc_type NULL=970). Sigue siendo PROPUESTA: el SQL del T2 lo aplica Alberto; este instrumento no escribe.
- **CONFLICT** → NO aplicar `product_model` de s83; Alberto decide fuente (patron FS2-1). Acotado (§3).
- **WEAK residual** → el juez no pudo decidir (contenido generico/granularidad) → Alberto o se deja.
- **UNMAPPED** → el source_file de s83 no tiene documento activo → fuera del alcance del T2 (solo revisiones superseded, o docs no ingestados).
- **IDIOMA (§4)** y **MARCA (§5)** son ejes SEPARADOS: una fila AUTO_CLEAN en pm puede aun aparecer ahi. El idioma es de hecho una CORRECCION probable que s83 aporta al T2.

## 7. Honestidad del instrumento — lo que NO juzga

- **Eje primario = `product_model`** (unico campo con valor en ambos lados → pre-filtro exacto recall-safe $0). AUTO_CLEAN determinista = SOLO corroboracion exacta/subset; todo lo demas va al juez.
- **No hay CONFLICT determinista.** Un pm string-disjunto (§3b) NO es conflicto por si mismo: puede ser familia/variante ('2X-AE1' vs '2X-A Tactil'), ruido de filename ('NRT-586T' vs source-file '15090SP'), o descripcion generica de s83. Solo el juez, leyendo contenido, decide CONFLICT.
- **AUTO_CLEAN = etiqueta corroborada, NO verdad de campo.** Sigue siendo una PROPUESTA para el T2.
- **`language`/`doc_type`/`marca` son advisory** (ejes ortogonales; DB mayormente NULL en language/doc_type → s83 RELLENA). La marca sufre el sello OEM (s55/s78) → solo `review`, nunca conflicto.
- **El juez LLM solo mira `product_model`** sobre contenido; no verifica correccion tecnica del manual. Es una augmentacion sobre WEAK, FUERA del contrato de determinismo 2x (la parte $0 si es 2x-identica).
- **doc-level `product_model` puede ser ruidoso** (filename-derived; census/T3). Por eso un CONFLICT es «el contenido CONTRADICE a s83», no «s83 mal»: Alberto adjudica.
