# s321 E3 — Packet de adjudicación v2 (generado 20260814T184710Z · SUPERSEDE al v1)

Los 55 docs AUTO ya están aplicados. Repesca v2 (s322c): los 12 «parse-fail»
del v1 eran el bug max_tokens=400 (mismo del censo #76), y las hermanas ahora
se resuelven a máquina (`hermanas_sujeto` con cita verificada FULL-TEXT).
Carril de evidencia ONLINE (primer uso) en las filas donde el corpus no llega.
NADA se aplica sin tu sí.

## §0 — Aplicables EN BLOQUE si asientes (23)

Alta + cita verificada full-text + sin variantes hermanas. Un «sí al §0» y
los aplico con el writer (CAS + findability), fila a fila.

- [ ] `PYX-L-15` → `PY X-L-15-CPR` · 21 chunks · 085501996d_PYX-L-15-CPR_Installation_manual_D-GB-F-RU-I
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento trata explícitamente el producto PY X-L-15-CPR como sujeto (título y aprobación VdS 0786-CPR-21563), siendo «PY X-L-15» solo la forma abreviada en la tabla técnica.
  - cita: «Operating and installation instruction for PY X-L-15-CPR beacon»
  - hermanas en content: — · canon-hits 9 · otros {'INA': 1}
- [ ] `ASD533` → `ASD 533-1` · 202 chunks · ASD533_TD_T140287es_e
  - clase: pm_prev_producto_real · LLM: **MANTENER_PREV** (alta, cita ✓)
  - razón LLM: El contenido (portada, título, hoja de datos 'Hoja de datos ASD 533 T 140 288') trata exclusivamente del ASD 533 sin mención alguna de la variante '-1', por lo que el pm actual «ASD533» es correcto y el canónico «ASD 533-1» no está respaldado por el documento.
  - cita: «# ASD 533

## Detector de humos por aspiración

## Descripción técnica»
  - hermanas en content: — · canon-hits 7 · otros {'SLM 35': 63, 'XLM 35': 61, 'RIM 35': 55, 'MCM 35': 36}
- [ ] `IS 28 Mk 4` → `IS 28 Mk 4 Banshee` · 16 chunks · BANI-G-24_Eng
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento trata como sujeto único al «IS 28 Mk 4 Banshee», nombre completo que aparece verbatim en el título y encabezados, por lo que el pm actual «IS 28 Mk 4» está truncado respecto al canónico.
  - cita: «IS 28 Mk 4 Banshee Audible Warning Device»
  - hermanas en content: — · canon-hits 2 · otros {'A-1': 2}
- [ ] `FAAST` → `FAAST 8100E` · 2 chunks · FAAST Understanding EN54-20_SP
  - clase: pm_prev_producto_real · LLM: **MANTENER_PREV** (alta, cita ✓) · repesca v2
  - razón LLM: El documento es una guía de aplicación EN54-20 que cubre 'cada modelo FAAST' a nivel de familia, no trata exclusivamente al FAAST 8100E como sujeto, por lo que el tag genérico FAAST es el correcto.
  - cita: «Se detallan las aplicaciones típicas dentro de cada clase EN54-20 (A-C), junto a las especificaciones relevantes de cada modelo FAAST.»
  - hermanas en content: — · canon-hits 2 · otros {}
- [ ] `WRA-PC-I02/WRA-RC-I02/WWA-PC-I02/WWA-RC-I02` → `W*A-*C-I02` · 6 chunks · I56-5005-002_D Notifier Sounder Strobe
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El contenido usa verbatim la designación comodín W*A-*C-I02 como sujeto del documento, cubriendo colectivamente las variantes rojas/blancas (coverage data RED/WHITE) que el pm actual lista con barras.
  - cita: «EN 54-17:2005

Fire detection and fire alarm systems - Short-circuit isolators.

W*A-*C-I02»
  - hermanas en content: — · canon-hits 1 · otros {'B501AP': 3, 'B501': 3, 'A-1': 2, '2001': 1}
- [ ] `LocatorPlus` → `Signaline LocatorPlus` · 16 chunks · LocatorPlus-Installation-Manual-1.3
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El contenido trata el producto consistentemente como «Signaline LocatorPlus» (marca Signaline HEAT), por lo que el canónico adjudicado es el sujeto real del documento y el tag actual «LocatorPlus» es solo una forma truncada.
  - cita: «The Signaline LocatorPlus is a dual zone module for monitoring up to two zones of Signaline FT or FT-R Digital Linear Heat Detection»
  - hermanas en content: — · canon-hits 15 · otros {'A-1': 1}
- [ ] `ID3000` → `ISO-RS232` · 1 chunks · MADT190_02
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento trata específicamente el conexionado de la tarjeta ISO-RS232 como sujeto principal; la central ID3000 solo se menciona como contexto de ubicación de la tarjeta.
  - cita: «Conexionado Tarjeta Aislada ISO-RS232 con PC / Impresora»
  - hermanas en content: — · canon-hits 2 · otros {'ID3000': 1}
- [ ] `ID3000` → `NGU` · 17 chunks · MADT190_05
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El documento son instrucciones de instalación cuyo sujeto es el módulo de red NGU; la ID3000 aparece solo como central anfitriona donde se instala.
  - cita: «# INSTALACIÓN DEL MÓDULO DE RED NGU

El módulo de red (NGU) (Ref.: 002-467) consta de una caja posterior (con tapa) con los siguientes componentes»
  - hermanas en content: — · canon-hits 41 · otros {'NGM': 24, 'IDR-6A': 4, '124-319': 1, 'M701': 1}
- [ ] `AFP-400` → `AFP4000` · 1 chunks · MADT231
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El contenido trata explícitamente la central AFP4000 (título y «CENTRAL AFP4000»), por lo que el tag actual AFP-400 es erróneo y debe corregirse al canónico.
  - cita: «EJEMPLO DE EXTINCIÓN EN LA AFP4000»
  - hermanas en content: — · canon-hits 2 · otros {}
- [ ] `AFP-400` → `AFP4000` · 1 chunks · MADT232
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El contenido del documento menciona explícitamente y en repetidas ocasiones la Central AFP4000 como sujeto (también «Conector de entradas digitales de la Central AFP4000»), no AFP-400.
  - cita: «Entre la fuente de alimentación y la Central **AFP4000** deberá instalarse dos líneas independientes de 24 Vdc»
  - hermanas en content: — · canon-hits 2 · otros {}
- [ ] `ZXCE` → `FIRECONTROL` · 8 chunks · MIE-MU-215
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El documento es el manual del software FIRECONTROL (requerimientos, instalación, arranque, parámetros de comunicación); la central ZXCE es solo el equipo destino sobre el que opera el programa, no el sujeto documentado.
  - cita: «Programa de Textos FIRECONTROL para centrales ZXCE

El programa de modificación de textos FIRECONTROL, trabaja bajo entorno de sistema operativo Windows»
  - hermanas en content: — · canon-hits 5 · otros {'ZXCE': 10}
- [ ] `DXc` → `MIW-INT` · 1 chunks · MIW-INT-La-central-DXC-indica-corto-tras-instalar-el-In
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El sujeto del documento es el interface MIW-INT (su configuración y avería LOEr); la central DXC es solo el contexto donde se manifiesta el problema, no el producto tratado.
  - cita: «¿Qué hacer en caso de la central DXC indicar corto trás instalar y autoprogramar el Interface MIW-INT?»
  - hermanas en content: — · canon-hits 3 · otros {}
- [ ] `iBox Modbus Server` → `IBOX-MBS-NID3000` · 39 chunks · MN-DT-958I_iBox-MBS-NID3000
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento es el manual de usuario del gateway iBox Modbus Server para centrales Notifier ID3000, cuyo código de producto explícito en portada es IBOX-MBS-NID3000, coincidiendo con el canónico adjudicado.
  - cita: «(IBOX-MBS-NID3000_EN / v10 r12 eng)»
  - hermanas en content: — · canon-hits 2 · otros {'ID3000': 24, 'ISO-RS232': 5, '816': 1, '1469': 1}
- [ ] `SENTOX IDI` → `SENTOX IDI+` · 49 chunks · MNDT513_SENTOX-IDI
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento es el manual de usuario e instalación del SENTOX IDI+ (con el sufijo '+'), mencionado consistentemente en portada, encabezados y secciones (p.ej. '3.1) FUNCIONAMIENTO DE LA CENTRAL DE GAS SENTOX IDI+'), por lo que el pm actual 'SENTOX IDI' omite el '+' y debe corregirse al canónico.
  - cita: «# SENTOX IDI+

## MANUAL DE USUARIO E INSTALACIÓN»
  - hermanas en content: — · canon-hits 58 · otros {'G-OUT16': 4, '2004': 2, '2001': 1, 'A-1': 1}
- [ ] `IBOX MODBUS SERVER` → `IBOX-MBS-NID3000` · 40 chunks · MNDT958
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El documento trata como sujeto único la pasarela iBox Modbus Server cuya referencia canónica IBOX-MBS-NID3000 aparece verbatim en portada y en 'Ref.: IBOX-MBS-NID3000'; las centrales ID3000/ID3002/ID60/ID50 son los sistemas integrados, no el producto del manual.
  - cita: «(IBOX-MBS-NID3000 / v10 r13 esp)»
  - hermanas en content: — · canon-hits 2 · otros {'ID3000': 26, 'ISO-RS232': 5, 'ID-60': 3, 'ID-50': 3}
- [ ] `theFirebeam BLUE` → `Firebeam Blue` · 28 chunks · Manual de usuario Issue 0165-02 v2 MI 546 es 2022 FIREB
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento trata exclusivamente el detector Firebeam Blue como sujeto (manual de usuario del producto BLUE con su app), por lo que corresponde alinear el product_model al canónico «Firebeam Blue».
  - cita: «Enhorabuena por adquirir el detector de humo de haz óptico reflejado the **fire**beam*BLUE*.»
  - hermanas en content: — · canon-hits 7 · otros {'70KIT140': 2, '140KIT160': 2, 'Solo CO': 1, 'A-1': 1}
- [ ] `ONE/ONE-LOOP` → `ONE 500` · 69 chunks · ONE500S01-MU - MANUAL DE USUARIO SERIE ONE v2.1
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El documento es el manual de usuario del sistema ONE cuyo único producto central es el ONE 500; ONE-LOOP aparece solo como tarjeta de expansión accesoria, por lo que no debe formar parte del product_model.
  - cita: «* **ONE 500**. Central de evacuación ampliable.
  - **ONE-BC**: Módulo de gestión de batería según EN54-4
  - **ONE-LOOP**: Tarjeta de expansión para sistemas d»
  - hermanas en content: — · canon-hits 2 · otros {'ONE-LOOP': 10, 'VAP 1': 8, 'ONE-BC': 2, 'TFL-2': 1}
- [ ] `ID-3000` → `UCIP` · 1 chunks · UCIP-Como-conectar-con-TG
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El sujeto del documento es el UCIP (su configuración, IP por defecto, comandos); ID-3000 solo aparece como una de varias centrales compatibles con distintas velocidades, no como tema del documento.
  - cita: «Como configurar el UCIP para que comunique vía IP con el TG»
  - hermanas en content: — · canon-hits 7 · otros {'ID-50': 1, 'ID3000': 1}
- [ ] `VSN-232` → `VSN 4 PLUS` · 3 chunks · VSN4-PLUS_ITA
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El contenido trata inequívocamente el panel VSN4-PLUS como sujeto (título, código de documento y diagramas), no el VSN-232 del tag actual.
  - cita: «Manuale Utente
Doc. M-061.1-VSN4-PLUS-ITA Rev A.1

VSN4-PLUS»
  - hermanas en content: — · canon-hits 7 · otros {'VSN4-PLUS': 7}
- [ ] `DTP/Booster` → `020-543` · 4 chunks · 997-267-000-6_Eng
  - clase: no_dominante · LLM: **RETAG_CANONICO** (alta, cita ✓) · repesca v2
  - razón LLM: El documento trata como sujeto único el kit DTP/Booster cuyo número de parte canónico es 020-543, por lo que el pm actual y el canónico refieren al mismo producto y procede el retag al identificador canónico.
  - cita: «The Dual Transmission Path (DTP)/Booster kit (PN: 020-543) is very simple to fit to the main chassis»
  - hermanas en content: — · canon-hits 2 · otros {'PSU7A': 5}
- [ ] `SP-20` → `NFXI-BF-WCH` · 4 chunks · D 1149-1 BGL Notifier
  - clase: no_dominante · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El contenido trata una base sonora/VAD con detector (EN 54-23/EN 54-17) cuyo bloque de certificación identifica explícitamente el producto como NFXI-BF-WCH, mientras que «SP-20» solo aparece como referencia a un documento externo (SP20-3250) de especificaciones del aislante.
  - cita: «EN 54-17:2005

Fire detection and fire alarm
systems - Short-circuit isolators.

NFXI-BF-WCH»
  - hermanas en content: — · canon-hits 1 · otros {'B501AP': 2, 'B501': 2}
- [ ] `CASE-32` → `NRXI-GATE` · 12 chunks · I56-4207-001 NRXI-GATE Gateway Web
  - clase: no_dominante · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: El documento es la instrucción de instalación del gateway NRXI-GATE como sujeto principal, y el pm actual «CASE-32» no corresponde al contenido.
  - cita: «The NRXI-GATE is an advanced RF device designed for use with Notifier addressable intelligent fire systems that use a compatible proprietary communication proto»
  - hermanas en content: — · canon-hits 7 · otros {'B501AP': 8, 'B501': 8, '2004': 2, 'INA': 2}
- [ ] `IBOX BACNET` → `IBOX-BAC-NID3000` · 85 chunks · MNDT960I_iBox-BACnet
  - clase: no_dominante · LLM: **RETAG_CANONICO** (alta, cita ✓)
  - razón LLM: La portada del manual identifica explícitamente el producto como IBOX-BAC-NID3000, gateway para integrar centrales Notifier ID3000 en BACnet/IP, coincidiendo con el canónico adjudicado.
  - cita: «(IBOX-BAC-NID3000 / r1 eng)»
  - hermanas en content: — · canon-hits 3 · otros {'INA': 82, 'ID3000': 74, 'ID2000': 10, 'ISO-RS232': 10}


## §0-bis — Hermanas RESUELTAS con cita (20)

Alta + cita ✓ + hermanas presentes, PERO el doc muestra sujeto ÚNICO (las
hermanas son accesorios/referencias) con cita verificada de ese papel. Un
«sí al §0-bis» los aplica igual; si dudas de alguna, sácala a §1.

- [ ] `DXc` → `B501AP` · 1 chunks · DXC-Como-conectar-una-sirena-de-lazo
  - clase: pm_prev_producto_real · LLM: **MANTENER_PREV** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El sujeto del documento es la central DXc (cómo conectar una sirena de lazo a ella); la B501AP solo se menciona como base/accesorio de montaje de la sirena, no como producto tratado.
  - cita: «DXC Como conectar una sirena de lazo»
  - hermanas (unico): «Este artículo es válido para la conexión de una sirena de lazo que tiene la base B501AP.»
  - hermanas en content: ['B501'] · canon-hits 1 · otros {'B501': 1}
- [ ] `SMB-500` → `NRX-M711` · 15 chunks · I56-4294-002 NRX-M711 Module
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación del módulo NRX-M711; el SMB-500 (SMB500) es solo la caja trasera accesoria incluida en la lista de partes y el NRXI-GATE es únicamente el gateway compatible referenciado, no un sujeto del documento.
  - cita: «NRX-M711
RADIO SYSTEM INPUT/OUTPUT MODULE
INSTALLATION INSTRUCTIONS»
  - hermanas (unico): «El módulo de entrada-salida de radio NRX-M711 es un dispositivo de RF operado por batería diseñado para usarse con el portal de radio NRXI-G»
  - hermanas en content: ['NRXI-GATE'] · canon-hits 6 · otros {'SMB500': 4, 'INA': 3, 'NRXI-GATE': 2}
- [ ] `AT-60` → `M701E` · 9 chunks · I56-4405-002 M701E
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación exclusivo del módulo de salida M701E; la mención a la serie M700 es solo contexto de familia, y el pm actual AT-60 no aparece en el contenido.
  - cita: «INSTALLATION INSTRUCTIONS FOR THE M701E OUTPUT MODULE»
  - hermanas (unico): «The M700 series of modules are a family of microprocessor controlled interface devices permitting the monitoring and/or control of auxiliary»
  - hermanas en content: ['M701'] · canon-hits 16 · otros {'M701': 16}
- [ ] `UCIP` → `UCIP-GPRS` · 1 chunks · UCIP-Borrar-configuracion-completa
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata un único sujeto, el UCIP-GPRS (así se nombra explícitamente en la pregunta), y «UCIP» funciona solo como forma abreviada del mismo producto en el título y referencias cruzadas, por lo que corresponde retaguear al canónico UCIP-GPRS.
  - cita: «¿Como borrar la configuración de UCIP-GPRS?»
  - hermanas (unico): «# UCIP - Borrar configuración completa.

**Question** ¿Como borrar la configuración de UCIP-GPRS?»
  - hermanas en content: ['UCIP', 'UCIP GPRS'] · canon-hits 1 · otros {'UCIP': 4, 'UCIP GPRS': 1}
- [ ] `ID-3000` → `UCIP-GPRS` · 1 chunks · UCIP-Conectar-con-equipo-via-Serie
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata la conexión serie con el UCIP-GPRS como sujeto único (UCIP es la misma familia/denominación genérica), mientras que ID3000 solo aparece como central referenciada en la tabla de cableado, no como producto del documento.
  - cita: «Requisitos y herramientas para conectar con *UCIP-GPRS*, por puerto SERIE.»
  - hermanas (unico): «Es necesario disponer de la herramienta de configuración para UCIP **"Consola V.2.2.2"**»
  - hermanas en content: ['UCIP', 'UCIP GPRS'] · canon-hits 1 · otros {'UCIP': 9, 'ID3000': 2, 'VSN2': 1, 'ID-50': 1}
- [ ] `Z728` → `Z728.H` · 3 chunks · Z728_installation manual
  - clase: pm_prev_producto_real · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata exclusivamente el modelo Z728.H (versión de alto rendimiento) como sujeto único, sin contenido propio para la variante base Z728.
  - cita: «Barrera Zener                                                                                            Z728.H»
  - hermanas (unico): «Versión de alto rendimiento»
  - hermanas en content: ['Z728'] · canon-hits 2 · otros {'Z728': 2, '2001': 1, 'INA': 1}
- [ ] `LOCAL-360` → `SDX-751EM` · 13 chunks · I56-1306-002_SDX-751EM
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El pm actual 'LOCAL-360' es un falso positivo extraído de la frase 'local 360° visible sensor indication'; el documento trata única y explícitamente el SDX-751EM (la 'hermana' SDX-751 es solo una subcadena del propio modelo, sin contenido propio).
  - cita: «INSTALLATION AND MAINTENANCE INSTRUCTIONS FOR MODEL SDX-751EM ANALOGUE ADDRESSABLE PHOTOELECTRONIC SMOKE SENSOR»
  - hermanas (unico): «Model SDX-751EM analogue addressable photoelectronic sensors are plug-in type smoke sensors that combine a photoelectronic sensing chamber w»
  - hermanas en content: ['SDX-751'] · canon-hits 6 · otros {'SDX-751': 6, 'B501': 4, 'INA': 2}
- [ ] `PA400` → `DH500ACDC-E` · 23 chunks · I56-2166-02R DH500ACDC-E
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación y mantenimiento del DH500ACDC-E como único sujeto; PA400 aparece solo como dispositivo auxiliar en la tabla de consumos eléctricos (marcado con asterisco), y 'DH500' es simplemente parte del nombre del producto canónico, no una variante hermana con contenido propio.
  - cita: «DH500ACDC-E Intelligent Air Duct Smoke Detector Housing»
  - hermanas (unico): «The DH500ACDC-E Air Duct Detector Housings are used with System Sensor's analogue addressable photoelectronic detector heads (purchased sepa»
  - hermanas en content: ['DH500'] · canon-hits 18 · otros {'RTS451': 27, 'DH500': 19}
- [ ] `TO-28` → `M710-CZR` · 10 chunks · I56-3674-000 M710-CZR
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación exclusivo del M710-CZR (las menciones a M700/M710 son solo referencias a la familia, y el pm actual 'TO-28' no aparece como sujeto en el contenido).
  - cita: «INSTALLATION INSTRUCTIONS FOR M710-CZR CONVENTIONAL ZONE INTERFACE MODULE»
  - hermanas (unico): «The M700 modules are a family of microprocessor controlled interface devices permitting the monitoring and/or control of auxiliary devices. »
  - hermanas en content: ['M710'] · canon-hits 14 · otros {'M710': 14, 'B401': 2, '6500R': 2}
- [ ] `THE-6500` → `MI-LPB2-S2I` · 19 chunks · I56-3879-000 MI-LPB2-S2I_EN
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata exclusivamente el MI-LPB2-S2I como sujeto único; el pm actual THE-6500 es erróneo (los códigos 6500-LRK/SMK/MMK son solo accesorios de montaje) y no hay contenido propio de la hermana MI-LPB2.
  - cita: «INSTALLATION AND MAINTENANCE INSTRUCTIONS MI-LPB2-S2I REFLECTED TYPE PROJECTED BEAM SMOKE DETECTOR»
  - hermanas (unico): «The model MI-LPB2-S2I is an addressable long range projected beam smoke detector designed to provide open area protection.»
  - hermanas en content: ['MI-LPB2'] · canon-hits 9 · otros {'MI-LPB2': 9, 'A-1': 1}
- [ ] `EL-6500` → `MI-LPB2-S2I` · 19 chunks · I56-3879-000 MI-LPB2-S2I_ES
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación y mantenimiento del MI-LPB2-S2I como único sujeto; 'MI-LPB2' solo aparece como subcadena del nombre completo y las referencias 6500-* son accesorios (LRK/MMK/SMK), no el producto EL-6500 etiquetado actualmente.
  - cita: «INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO DETECTOR DE HUMO POR RAYO DEL TIPO REFLEJADO MI-LPB2-S2I»
  - hermanas (unico): «El modelo MI-LPB2-S2I es un detector de humo analógico por rayo proyectado de largo alcance, diseñado para proteger áreas diáfanas.»
  - hermanas en content: ['MI-LPB2'] · canon-hits 9 · otros {'MI-LPB2': 9, 'A-1': 2, '6500R': 1}
- [ ] `FROM-01` → `IM-10EA` · 11 chunks · I56-3918-001 IM-10EA_multi
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata exclusivamente el IM-10EA como sujeto (título, wiring, etiqueta CE); 'IM-10' es solo subcadena del propio modelo y el pm actual 'FROM-01' proviene de un texto de diagrama ('FROM PANEL...'), no de un producto.
  - cita: «# IM-10EA

# Ten Input Monitor Module»
  - hermanas (unico): «All wiring to the IM-10EA is done via terminal blocks»
  - hermanas en content: ['IM-10'] · canon-hits 8 · otros {'IM-10': 8, 'INA': 1}
- [ ] `FROM-01` → `CR-6EA` · 12 chunks · I56-3920-001 CR-6EA_multi
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata exclusivamente el módulo CR-6EA como sujeto (título, especificaciones, figuras y etiqueta CE lo nombran); 'CR-6' es un falso positivo por subcadena de CR-6EA y 'FROM-01' es un error de extracción del rango de direcciones ('from 01 to 94').
  - cita: «# CR-6EA

# Six Relay Control Module»
  - hermanas (unico): «**EN54-18:2005**<br/>**INPUT/OUTPUT DEVICE**<br/>**EN54-17: 2006**<br/>**SHORT CIRCUIT ISOLATOR**<br/>**CR-6EA**»
  - hermanas en content: ['CR-6'] · canon-hits 13 · otros {'CR-6': 13, 'INA': 1}
- [ ] `EN-54-25` → `NRX-SMT3` · 19 chunks · I56-4205-001 NRX-SMT3 Web
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación del sensor NRX-SMT3 (único sujeto); el pm actual «EN-54-25» es una norma citada, no un producto, y NRXI-GATE aparece solo como pasarela asociada, no como sujeto con contenido propio.
  - cita: «The NRX-SMT3 radio sensor is a battery operated RF device designed for use with the NRXI-GATE radio gateway. It contains a wireless transceiver and runs on a No»
  - hermanas (unico): «designed for use with the NRXI-GATE radio gateway»
  - hermanas en content: ['NRXI-GATE'] · canon-hits 4 · otros {'B501RF': 8, 'B501': 8, 'A-1': 7, '2004': 2}
- [ ] `WITH-48` → `NRX-REP` · 12 chunks · I56-4208-001 NRX-REP Repeater Web
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento trata exclusivamente del repetidor NRX-REP como sujeto; el pm actual «WITH-48» es un artefacto de extracción del diagrama de pesos (48 g), y NRXI-GATE aparece solo como pasarela asociada, no como sujeto propio.
  - cita: «NRX-REP
RADIO SYSTEM REPEATER
INSTALLATION INSTRUCTIONS»
  - hermanas (unico): «El repetidor NRX-REP es un dispositivo vía radio para el uso con la pasarela vía radio NRXI-GATE»
  - hermanas en content: ['NRXI-GATE'] · canon-hits 6 · otros {'B501RF': 8, 'B501': 8, '2004': 1, 'NRXI-GATE': 1}
- [ ] `EN-54-25` → `NRX-OPT` · 12 chunks · I56-4225-001 NRX-OPT Web
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación del sensor NRX-OPT (sujeto único); el pm actual «EN-54-25» es una norma de conformidad mal extraída y NRXI-GATE solo aparece como pasarela compatible, no como sujeto.
  - cita: «NRX-OPT WIRELESS OPTICAL SMOKE SENSOR INSTALLATION AND MAINTENANCE INSTRUCTIONS»
  - hermanas (unico): «The NRX-OPT radio sensor is a battery operated RF device designed for use with the NRXI-GATE radio gateway.»
  - hermanas en content: ['NRXI-GATE'] · canon-hits 6 · otros {'B501RF': 11, 'B501': 11, '2004': 3, 'NRXI-GATE': 3}
- [ ] `MM-82` → `MI-DCMOE` · 7 chunks · I56-4407-001 MI-DCMOE
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El pm actual «MM-82» es un artefacto de extracción (proviene de la dimensión «82 mm»); el documento trata exclusivamente el MI-DCMOE como sujeto, y la supuesta hermana MI-DCMO es solo un subtexto/substring del propio nombre, sin contenido propio.
  - cita: «EN INSTALLATION INSTRUCTIONS FOR THE MI-DCMOE OUTPUT MODULE»
  - hermanas (unico): «The MI-DCMOE is an output module that allows the control of auxiliary devices such as fire shutters or sounders.»
  - hermanas en content: ['MI-DCMO'] · canon-hits 15 · otros {'MI-DCMO': 15}
- [ ] `OF-48V` → `M701E-240` · 10 chunks · I56-4422-000 M701E-240
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación del módulo M701E-240 como único sujeto (el pm actual «OF-48V» es un artefacto de la nota sobre cables >48V); las menciones a M701E/M701/M700 son referencias genéricas a la serie y el M200E-SMB es solo accesorio de montaje.
  - cita: «M701E-240
INSTALLATION INSTRUCTIONS FOR MAINS SWITCHING OUTPUT MODULE»
  - hermanas (unico): «The M700 series of modules are a f»
  - hermanas en content: ['M701E', 'M701'] · canon-hits 13 · otros {'M701E': 13, 'M701': 13}
- [ ] `PA400` → `DH500ACDC-E` · 23 chunks · MIDT1041
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El documento es el manual de instalación de la carcasa DH500ACDC-E como sujeto único; PA400 aparece solo como accesorio en la tabla de consumos (marcado con asterisco) y DH500 es la misma familia del producto canónico, no un producto hermano con contenido propio.
  - cita: «CARCASA DEL DETECTOR ANALÓGICO DE HUMO POR CONDUCTO DE AIRE DH500AC/DC»
  - hermanas (unico): «Las carcasas de Detectores de Conducto de Aire DH500ACDC se utilizan con cabezas de detectores fotoeléctricos o iónicos direccionales analóg»
  - hermanas en content: ['DH500'] · canon-hits 11 · otros {'DH500': 35, 'RTS451': 27, 'Solo CO': 1, 'A-1': 1}
- [ ] `TO-3200M` → `MIW-INT` · 1 chunks · MIW-INT-Cuantos-expansores-puedo-conectar-al-Interface-
  - clase: ambigua_hermanas · LLM: **RETAG_CANONICO** (alta, cita ✓, hermanas ✓) · repesca v2
  - razón LLM: El pm actual «TO-3200M» es una extracción errónea de la distancia «hasta 3200m»; el documento trata al interface MIW-INT como sujeto y MIW-EXP solo aparece como dispositivo periférico que se conecta a él.
  - cita: «# MIW-INT - Cuantos expansores puedo conectar al Interface / pasarela»
  - hermanas (unico): «¿Cuantos expansores MIW-EXP puedo conectar al Interface / pasarela MIW-INT?»
  - hermanas en content: ['MIW-EXP'] · canon-hits 3 · otros {'MIW-EXP': 1}


## §1 — Una a una (4)

El residuo real — con la evidencia online adjunta (🌐: informa TU decisión;
no se escribe nada de ella sin tu sí).

- [ ] `FD2705R` → `FD2705-10R` · 9 chunks · 22318.18.08_-_aritech_ra_-_fd2705-10r_english_std_refle
  - clase: pm_prev_producto_real · LLM: **NO_DECIDIBLE** (baja) · repesca v2
  - razón LLM: parse-fail v2
  - cita: «—»
  - hermanas en content: — · canon-hits 0 · otros {'AT-25': 1}
  - 🌐 EVIDENCIA ONLINE (2026-08-14): «FD2705-10R» NO existe como modelo en el mercado: la familia Aritech serie 2000 es FD2705R (reflective beam 5-50 m) y FD2710R (50-100 m). El «canónico» adjudicado parece ARTEFACTO del nombre de fichero (fd2705-10r ≈ FD2705R+FD2710R), y el doc probablemente cubre AMBOS modelos.
    → recomendación: MULTI_VALOR «FD2705R/FD2710R» (o MANTENER FD2705R si el contenido solo trata el de 50 m) — y revisar el canónico FD2705-10R del doc_map, que sería artefacto.
    · «Aritech FD2705R 2000 Series Addressable Reflective Beam Detector (50m)» — https://www.acornfiresecurity.com/aritech-fd2705r-2000-series-addressable-reflective-beam-detector-50m
    · «Aritech FD2710R 2000 Series Addressable Reflective Beam Detector (100m)» — https://www.acornfiresecurity.com/aritech-fd2710r-2000-series-addressable-reflective-beam-detector-100m
    · «FD2710R 2000 series addressable reflective beam detector 50 to 100 m» — https://www.aritechfire.com.ph/sites/default/files/downloads-products/FD2710R%20%20Addr%20Beam%20Detector%20(100m).pdf
- [ ] `ZXrA` → `ZXR50A` · 1 chunks · Puesta-en-marcha-repetidor-ZXrA-en-central-CONNEXION
  - clase: pm_prev_producto_real · LLM: **NO_DECIDIBLE** (baja) · repesca v2
  - razón LLM: parse-fail v2
  - cita: «—»
  - hermanas en content: — · canon-hits 0 · otros {'IDR6A': 2, 'IDR-6A': 2, 'IDR-2A': 1}
  - 🌐 EVIDENCIA ONLINE (2026-08-14): ZXR50A SÍ existe: es el nombre del repetidor activo Morley-IAS en el mercado ESPAÑOL (manual oficial MIE-MI-440 «Repetidores ZXR50A y ZXR50P» en morley-ias.es). ZXr-A es el nombre UK del repetidor activo (manual 996-144 «ZXr-A & ZXr-P»). Todo apunta a MISMO producto con naming por mercado.
    → recomendación: RETAG_CANONICO a ZXR50A defendible si adjudicas que ZXr-A(UK)=ZXR50A(ES); alternativa conservadora: MANTENER ZXrA. GAP DE CORPUS candidato: el manual MIE-MI-440 (morley-ias.es) no está ingestado — ingestarlo anclaría la identidad con cita propia.
    · «Doc.MIE-MI-440 Repetidores ZXR50A y ZXR50P Manual de Instalación» — https://www.morley-ias.es/documentacion/morley/manualesdes/MIE-MI-440.pdf
    · «ZXr-A Document No. 996-144 Issue 02 operation & installation manual ZXr-P» — https://www.ravensecurity.co.uk/manuals/fire-alarm-user-manuals/996-144-ZX-Repeater-User-Manual.pdf
- [ ] `ART 535-x` → `ART 535-10` · 20 chunks · TD 003 006c_Technische Dokumentation_Externer Temperatu
  - clase: pm_prev_producto_real · LLM: **MULTI_VALOR** (alta, cita ✓) · repesca v2 · multi: `ART 535-10/ART 535-30`
  - razón LLM: El documento es la documentación técnica de la familia ART 535-x y dedica capítulos propios de funcionamiento e instalación a las variantes ART 535-10 y ART 535-30 (incluidas versiones 400 °C y EX), por lo que adjudicarlo solo a ART 535-10 sería incompleto.
  - cita: «| 4.1 | Sensor de temperatura externo ART 535-10 | 12 |

| 4.2 | Sensor de temperatura externo ART 535-10 / 400 °C | 12 |

| 4.3 | Sensor de temperatura externo»
  - hermanas (multi): «## 4.1 Sensor de temperatura externo ART 535-10

Sensor de temperatura externo para el detector térmico lineal SecuriSens® ADW 535-x para la»
  - hermanas en content: ['ART 535'] · canon-hits 21 · otros {'ART 535': 95, 'ADW 535-2': 7, 'ADW 535-1': 7, 'ADW 535-1 ATEX': 3}
- [ ] `ECN-96-200` → `MPS-24AE` · 1 chunks · 50478 RevA - MPS-24AE _Eng
  - clase: no_atestada · LLM: **RETAG_CANONICO** (baja, cita ✓) · repesca v2
  - razón LLM: El pm actual 'ECN-96-200' es solo un número de orden de cambio de ingeniería (ECN), no un producto; el documento es un aviso de modificación a 240 VAC del panel MPS-24AE (según título del documento), aunque el nombre del producto no aparece verbatim en el contenido muestreado.
  - cita: «This control unit has been modified for 240 VAC operation. Be advised that "240VAC" should replace any reference made to input power of "110-120 VAC"»
  - hermanas en content: — · canon-hits 0 · otros {}
  - 🌐 EVIDENCIA ONLINE (2026-08-14): MPS-24AE SÍ existe: versión 220 VAC de la fuente de alimentación principal Notifier MPS-24A (datasheet Honeywell DN-0786; «primary input power 220 V, 50/60 Hz»). El pm actual «ECN-96-200» no existe como producto — artefacto de extracción.
    → recomendación: RETAG_CANONICO a MPS-24AE (la repesca v2 ya lo recomendó con cita ✓; la confianza baja era por doc de 1 chunk — el online la sube).
    · «MPS-24A Main Power Supply … MPS-24AE (220 VAC version)» — https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/notifier-us/hon-ba-fire-dn-0786.pdf
    · «Notifier MPS-24A Power Supply» — https://firealarmdepot.com/products/notifier-mps-24a-power-supply


---
*Recibos: `s321_e3_atestacion_v1.json` · `s321_e3_llm_recomendaciones_v2.json`
(repesca s322c sobre v1 intacto) · `s322_e3_online_evidencia_v1.json` ·
writer aplicado `s321_e3_writer_aplicar_20260813T222611Z.json`.*
