# s288 A-CORE — packet QA-30 de P-B para adjudicacion — v2

**Que hay que decidir (spec F0(e)(iii)):** para cada documento, ¿el idioma PROPUESTO es el idioma del documento? Regla de aceptacion: **30/30 correctos -> gate (e) verde; cualquier fallo -> HALT y revision del detector** (y, si el fallo es de un label legacy, revision de la cohorte etiquetada — spec riesgo 8). Marca `[x] OK` o `[x] MAL` por ficha.

- cohorte P-B (activos, `language IS NULL`, detector v2 confianza alta): **394** documentos · `{'en': 108, 'es': 286}`
- muestra: **30** documentos, estratificada por idioma propuesto, round-robin determinista sobre `md5(document_id)`
- detector: **v2_endurecido** · muestra 10 chunks/doc · alta ⇔ >=20 marcadores Y >=2.0x el segundo, + supresion de token dominante (>50%) + cruce de familia >= 3.0x
- freeze: commit `41be442b87a6` · corpus sha `744f21af87de1df9` · determinismo 2x OK

**Aviso de honestidad:** el detector NO es fiable fuera de {es, en} (todos los labels `it`/`fr`/`pt`/`nl` del corpus se detectan como `en`). Si alguna ficha propone un idioma distinto de `es`/`en`, trata la propuesta como sospechosa por defecto.

**Blind spot declarado:** el FIX 2 solo degrada cuando el 2º idioma cruza familia (`en` vs romance); un documento realmente mixto **es+fr/it/pt** NO se degrada. Como ayuda, las fichas cuyo NOMBRE sugiere multi-idioma llevan la marca ⚠️ **PISTA MULTI-IDIOMA** (heuristica de nombre, ADVISORY, no entra en ningun veredicto): **2 de 30** fichas.

---

## 1. `65669851-7431-412f-b727-bd65af27a170` — propuesta: **en**

- stem: `MNDT951I`
- fichero: `MNDT951I.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 653, 'es': 1, 'fr': 0, 'it': 1, 'pt': 3}` · 2º idioma: `pt` (3) · margen: 217.667x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): [A large watermarked logo appears at the top of the page, showing a stylized letter "R" within a circle, overlaid on a cloudy sky background with a gradient effect from coral/pink on the left to blue on the right] *TG - NOTIFIER* *USER'S GUIDE* *MN-DT-951I (Rev.: 5.83) December 2004* USER'S GUIDE INDEX # <ins>SUBJECTS INDEX</ins> 1. INTRODUCTION ............................................................... <ins>1</

> **evidencia 2** (chunk_index 5): # NOTIFIER FIRE SYSTEMS [Company logo showing circular "N" symbol with "NOTIFIER FIRE SYSTEMS" text] (this key is usually labelled Esc and is placed in the top left side of the keyboard). * *To type* means that you must enter specific data. For instance, if you are told to type "C:\", you should press the keys corresponding to these given characters in the keyboard. * *To enter*. This general term will always refer t

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 2. `f1a60b0d-54af-42eb-bb25-d999a174336f` — propuesta: **es**  ⚠️ **PISTA MULTI-IDIOMA en el nombre: `['es', 'fr', 'gb', 'it']`**

- stem: `55350005 Manual Central Monoxido CMD-500 ES FR GB IT`
- fichero: `55350005 Manual Central Monoxido CMD-500 ES FR GB IT` · marca: Detnov
- marcadores por idioma: `{'en': 43, 'es': 381, 'fr': 40, 'it': 47, 'pt': 67}` · 2º idioma: `pt` (67) · margen: 5.687x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # GUIDE MANUAL ES GB FR IT *Monoxide control panels User's and installation guide* NO_CONTENT_HERE # MANUAL DEL USUARIO ES *Centrales de detección de monóxido* *Guía de instalación y usuario* NO_CONTENT_HERE # ÍNDICE 1- Introducción.............................................................................................................5 **1.1- Descripción General de la Serie.......................................

> **evidencia 2** (chunk_index 5): ## 2.5- Conexión baterías ### (Opcional. Necesita modulo) Las centrales de monóxido requieren dos baterías de 12V el alojamiento esta preparado para baterías de 12V 2.3A/h y para baterías de 12V 7A/h. Las baterías deben conectarse en serie para el correcto funcionamiento de las centrales. El cable que se suministra con la central debe conectarse de forma que una el polo positivo de una batería con el polo negativo de

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 3. `84365c09-608f-4b5e-abc3-ff610a7acd41` — propuesta: **en**

- stem: `00-3280-507-4003-03_r003_2x-a_series_quick_installation_guide_en`
- fichero: `00-3280-507-4003-03_r003_2x-a_series_quick_installation_guide_en.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 202, 'es': 0, 'fr': 0, 'it': 1, 'pt': 4}` · 2º idioma: `pt` (4) · margen: 50.5x · chunks muestreados: 4

> **evidencia 1** (chunk_index 0): KIDDE COMMERCIAL # 2X-A Series Quick Installation Guide ## Overview This document includes quick installation information for your 2X-A control panel. For detailed installation information (including EN 54-13 requirements) and for configuration options, see the product installation manual. **WARNING:** Electrocution hazard. To avoid personal injury or death from electrocution, remove all sources of power and allow st

> **evidencia 2** (chunk_index 2): # Overview of typical fire system connections using a single Class A loop [Technical diagram showing a fire system connection schematic with the following components and labels: - Top section: A loop circuit with circular symbols (detectors), a butterfly valve symbol, and rectangular boxes connected in series - Middle section: Three vertical panels with multiple connection points, showing 15 kΩ resistors at various l

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 4. `0426c906-5080-499a-afb3-f45766907458` — propuesta: **es**

- stem: `HLSI-MN-963_POL-200-TS`
- fichero: `HLSI-MN-963_POL-200-TS` · marca: Morley
- marcadores por idioma: `{'en': 29, 'es': 247, 'fr': 24, 'it': 21, 'pt': 40}` · 2º idioma: `pt` (40) · margen: 6.175x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): Honeywell | Manual de usuario # POL-200-TS ## HERRAMIENTA DE DIAGNÓSTICO DEL LAZO POL-200-TS Manual de Usuario # Información de seguridad ⚠️ **¡Importante!:** *Antes de conectar cualquier cable externo, compruebe que el cable de lazo NO está conectado a la central por ninguno de los dos extremos del lazo.* Compruebe la correcta conexión de los terminales y que no existe ninguna tensión externa entre los cables que se

> **evidencia 2** (chunk_index 5): # 4. Lazo POL-200-TS device La herramienta reconoce los detectores y los módulos en el lazo, no es necesario conectarlo al panel de detección (FACP). El POL-200-TS es compatible con el protocolo CLIP diseñado para gestionar 99 detectores y 99 módulos en el lazo y también con el Protocolo Avanzado diseñado para gestionar 159 detectores y 159 módulos. En el menú **auto-programación**, nos identificará el número de dete

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 5. `f763235d-17dc-477e-b736-d45571c7f992` — propuesta: **en**

- stem: `WFDEN_Manual_I56-4051`
- fichero: `WFDEN_Manual_I56-4051` · marca: System Sensor
- marcadores por idioma: `{'en': 354, 'es': 5, 'fr': 2, 'it': 0, 'pt': 13}` · 2º idioma: `pt` (13) · margen: 27.231x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): I56-4051-003R # INSTALLATION AND MAINTENANCE INSTRUCTIONS System Sensor Logo 3825 Ohio Avenue, St. Charles, Illinois 60174 1-800-SENSOR2, FAX: 630-377-6495 www.systemsensor.com # WFDEN Vane-type Water flow Detector ## SPECIFICATIONS Contact Ratings: 10 A @ 125/250 VAC ~ ; 2.5 A @ 24 VDC ⚌ Triggering Flow Rate: Refer to Table 1 Static Pressure Rating (maximum): 17.25 bar (250 psi) (1725 KPa); 16 bar (VdS) Operating Te

> **evidencia 2** (chunk_index 5): ## FIGURE 1. MOUNTING DIMENSIONS: [Technical drawing showing a waterflow detector with the following labeled dimensions and components: - 8.9 CM (3.5") width at top - 6.6 CM (2.6") height measurement - PIPE DIAMETER PLUS 12.7 CM (5") - U-BOLT NUT (top and bottom) - PIPE SADDLE - PIPE (main body) - PIPE VANE - OVERALL WIDTH = PIPE DIAMETER + 6.4 CM (2.5") - Drawing reference: W0384-00] ## FIGURE 2. LOCATION OF MOUNTIN

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 6. `123dc496-4b91-43a5-8855-c3998ed20d37` — propuesta: **es**

- stem: `MIE-MC-530`
- fichero: `MIE-MC-530.pdf` · marca: Morley
- marcadores por idioma: `{'en': 40, 'es': 328, 'fr': 17, 'it': 44, 'pt': 43}` · 2º idioma: `it` (44) · margen: 7.455x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): MORLEY IAS FIRE SYSTEMS by Honeywell # MK-ZX Documento No.MIE-MC-530rv001 Manual de Funcionamiento MORLEY-IAS Fire6 Serie ZX # Índice **1 INTRODUCCIÓN......................................................................................................................... 3** 1.1 AVISO .................................................................................................................................... 3

> **evidencia 2** (chunk_index 5): # 3 Instalación del Programa Fire6 El programa se entrega en soporte óptico totalmente instalado. Abra el Explorador de Windows y seleccione la unidad de lector de Discos de su PC (CD) donde haya insertado el disco del Fire6, haciendo doble clic sobre ésta con el botón izquierdo del ratón. Se mostrarán los archivos que contiene el disco. -Seleccione todos los archivos, desde **Edición** del Explorador de Windows, hac

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 7. `f8132ff7-ef29-478e-8304-c94e60fd4288` — propuesta: **en**

- stem: `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_panel_compatibility_list_900_series_protocol`
- fichero: `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_panel_compatibility_list_900_series_protocol.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 137, 'es': 0, 'fr': 3, 'it': 0, 'pt': 2}` · 2º idioma: `fr` (3) · margen: 45.667x · chunks muestreados: 8

> **evidencia 1** (chunk_index 0): KIDDE COMMERCIAL # 2X-A and ZP2-A Series Addressable Control Panel Compatibility List (900 Series Protocol) ## Introduction This document lists the products compatible for use with 2X-A and ZP2-A Series fire alarm control panels (firmware 4.x only) when using the 900 Series protocol. **WARNING:** Only those devices included in this publication are tested and confirmed compatible for use with 2X-A and ZP2-A Series fir

> **evidencia 2** (chunk_index 4): | Device range | Model | Description | Notes | | ------------------------------------ | --------------- | ------------------------------------------------------------------------------ | ----------------------------------------- | | 950 Series Notification | AS967WRCI\* | Apollo XP95 Loop-powered open area sounder/VID with isolator (clear lens) | | | 950 Series Notification | DB952IAS\* | Apollo XP95 85/92 dB integra

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 8. `08828182-830a-4776-a6c4-32ab605c4665` — propuesta: **es**

- stem: `MIE-MI-010`
- fichero: `MIE-MI-010.pdf` · marca: Morley
- marcadores por idioma: `{'en': 47, 'es': 306, 'fr': 26, 'it': 39, 'pt': 66}` · 2º idioma: `pt` (66) · margen: 4.636x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MORLEY IAS ## FIRE SYSTEMS ### by Honeywell # MPS Documento No.MIE-MI-010rv002 # Manual de Instalación www.morley-ias.es [Icon showing three figures representing people in different lifting positions] [Warning triangle icon with exclamation mark] # INSTRUCCIONES IMPORTANTES DE SEGURIDAD ## Medidas de seguridad • No levante cargas pesadas sin ayuda | => < 18 Kg | \[Icon: single person lifting] | => 32 - 55 Kg | \[Ic

> **evidencia 2** (chunk_index 5): # Características de las fuentes de alimentación MPS15, MPS25, MPS50. Las fuentes de alimentación (F.A.) de Morley-IAS MPS15, MPS25 y MPS50 se han diseñado cumpliendo los criterios de la norma EN54-4 con el fin de suministrar alimentación de apoyo a sistemas de control de incendio. Revise la reglamentación vigente para una correcta instalación de la misma y de los circuitos y equipos que desee alimentar. Todos los ca

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 9. `aac0d826-9830-4f6e-a9a8-dc0159bffee7` — propuesta: **en**

- stem: `10-5106-501-55nc-05_r005_iu2055nc_installation_sheet_ml`
- fichero: `10-5106-501-55nc-05_r005_iu2055nc_installation_sheet_ml.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 293, 'es': 59, 'fr': 6, 'it': 8, 'pt': 12}` · 2º idioma: `es` (59) · margen: 4.966x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # aritech # IU2055NC Conventional Zone Monitor Unit Installation Sheet EN DA ES FR HU IT LT NL PL PT RO SV TR ## 1 ## 2 J5 (5) 5 6 7 8 9 3 4 5 6 4 2 10 2 7 2 1 11 1 8 1 0 12 0 9 J4 (6) COM2 COM1 IND (4) \+ + - \+ - DET+ DET- (3) (1) + (2) (7) © 2025 Kidde Commercial. All rights reserved. 1 / 32 P/N 10-5106-501-55NC-05 • REV 005 • 29MAY25 # 3 [Wiring diagram showing: (1) DET+ and DET- terminals at top with connection 

> **evidencia 2** (chunk_index 5): # Specifications | Device operating voltage | 21 to 28 VDC | | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | | Device current consumption<br/>Standby<br/>Alarm | <br/>< 15 mA<br/>< 40 mA | | Remote LED current | 3.6 mA | | Zone operating voltage (in standby) | 17.5 to 18.5 VDC | | Zone cable resistance<b

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 10. `0e9330c8-2c53-4941-bf4f-17fe40adbe84` — propuesta: **es**

- stem: `MIE-MI-530rv001`
- fichero: `MIE-MI-530rv001` · marca: Morley
- marcadores por idioma: `{'en': 1, 'es': 122, 'fr': 10, 'it': 18, 'pt': 16}` · 2º idioma: `it` (18) · margen: 6.778x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MORLEY IAS # FIRE SYSTEMS ## by Honeywell # ZX2e # ZX5e Documento No.MIE-MI-530 rev.001 # manual de instalación **manual para el instalador.** MORLEY-IAS Paneles de Incendio ZX2e / ZX5e # Índice ## 1 INTRODUCCIÓN......................................................................................................................... 5 1.1 AVISO ........................................................................

> **evidencia 2** (chunk_index 5): ## Índice de Tablas TABLA 1 – CONTENIDO.......................................................................................................................... 8 TABLA 2 – LONGITUDES TÍPICAS RECOMENDADAS................................................................................. 17 TABLA 3 – LISTA DE EQUIPOS PERIFÉRICOS COMPATIBLES .................................................................... 26 TABLA 4

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 11. `637cc4d7-9e96-4545-9202-d6cb3463e701` — propuesta: **en**

- stem: `2x-at-f2-fb-p-161721-es`
- fichero: `2x-at-f2-fb-p-161721-es.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 138, 'es': 15, 'fr': 1, 'it': 4, 'pt': 1}` · 2º idioma: `es` (15) · margen: 9.2x · chunks muestreados: 5

> **evidencia 1** (chunk_index 0): KIDDE COMMERCIAL # 2X-AT-F2-FB-P **Addressable fire panel with tocuhscreen fire brigade controls, 2 loop, with bigger PSU** ## Overview The new 2X-A series life safety control systems bring the speed and functionality of high-end intelligent processing to small to mid-sized addressable applications. Based on 2X series learned experience and with complete backwards compatibility, the new 2X-A features an attractive co

> **evidencia 2** (chunk_index 2): # 2X-AT-F2-FB-P **Addressable fire panel with tocuhscreen fire brigade controls, 2 loop, with bigger PSU** ## Especificaciones técnicas ### General | Interfaz usuario | Con controles de Bomberos | | ----------------------------------------------------- | ------------------------- | | Capacidad máxima del sistema (número de dispositivos) | hasta 32512 | | Tamaño de la red (nodos) | hasta 64 | ### Eléctrico | Tipo de f

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 12. `a2bb8ee1-b20b-4f20-9a72-a59f6f560a0a` — propuesta: **es**

- stem: `Conexionado-del-modulo-M710-CZ-MI-DCZM`
- fichero: `Conexionado-del-modulo-M710-CZ-MI-DCZM.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 0, 'es': 20, 'fr': 0, 'it': 1, 'pt': 6}` · 2º idioma: `pt` (6) · margen: 3.333x · chunks muestreados: 1

> **evidencia 1** (chunk_index 0): # Conexionado del módulo M710-CZ / MI-DCZM **Question** ¿Cómo conectar el módulo M710-CZ o MI-DCZM? **Answers El módulo M710-CZ no se puede instalar en zonas clasificadas con detectores de seguridad intrínseca.** La instalación de la zona convencional debe ser conforme a la normativa EN54-14: * No incluir dentro de la zona detectores y pulsadores * Nº máximo de pulsadores 10 * Nº máximo de detectores 32 Para conectar

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 13. `c96bb93b-115e-42ef-920d-56a00201861c` — propuesta: **en**

- stem: `I56-3888-010 FAAST LT-200 Adv Guide`
- fichero: `I56-3888-010 FAAST LT-200 Adv Guide` · marca: Xtralis
- marcadores por idioma: `{'en': 314, 'es': 0, 'fr': 0, 'it': 0, 'pt': 3}` · 2º idioma: `pt` (3) · margen: 104.667x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # FAAST LT-200 ## FIRE ALARM ASPIRATION SENSING TECHNOLOGY® ## ADVANCED SET-UP AND CONTROL GUIDE ## CONTENTS | Introduction. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1 | Further PipeIQ™ Capabilities. . . . . . . . . . . . . . . . . . . . . . . . . . . 5 | | | | ------------------------------------------------------------------------------------------------- | -----------------

> **evidencia 2** (chunk_index 5): ## <ins>Service Mode</ins> When the FAAST LT-200 device is in *Normal*, the *Service Mode* state is entered automatically when the front cover is opened. The FAAST LT-200 unit switches off the power to the unit. Once the service action is complete, and the front cover is closed, the FAAST LT-200 device restarts automatically. Note that when leaving *Service Mode*, a unit will always run the initialise routine, re-cal

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 14. `6096bdf6-27b6-41bb-a03a-e65bf90b5ea9` — propuesta: **es**

- stem: `MIE-MU-530rv001`
- fichero: `MIE-MU-530rv001` · marca: Morley
- marcadores por idioma: `{'en': 31, 'es': 188, 'fr': 9, 'it': 18, 'pt': 33}` · 2º idioma: `pt` (33) · margen: 5.697x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MORLEY IAS FIRE SYSTEMS # by Honeywell # ZX2e # ZX5e Documento No. MIE-MU-530rev.001 # Manual de Funcionamiento MORLEY-IAS PANELES DE INCENDIO ZX2e/ZX5e # Índice **1 INTRODUCCIÓN......................................................................................................................... 4** 1.1 AVISO ........................................................................................................

> **evidencia 2** (chunk_index 5): # 2 Niveles de acceso de usuario ## 2.1 Definición de nivel * Las centrales de alarma de incendio ZX1E, ZX2E y ZX5E disponen de tres niveles de acceso para el usuario. * En los tres niveles, los LEDS indican la condición de la instalación. Los LEDs de zona indican la ubicación de cualquier alarma de incendio o avería y la pantalla alfanumérica ofrece información más detallada sobre la alarma o avería. * En el NIVEL D

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 15. `537a0275-920a-4e49-96ef-8d6d4570f06f` — propuesta: **en**

- stem: `156-0551-005R EPS10_Eng`
- fichero: `156-0551-005R EPS10_Eng` · marca: System Sensor
- marcadores por idioma: `{'en': 301, 'es': 0, 'fr': 0, 'it': 1, 'pt': 18}` · 2º idioma: `pt` (18) · margen: 16.722x · chunks muestreados: 8

> **evidencia 1** (chunk_index 0): INSTALLATION AND MAINTENANCE INSTRUCTIONS ![System Sensor Logo] 3825 Ohio Avenue, St. Charles, Illinois 60174 1-800-SENSOR2, FAX: 630-377-6495 www.systemsensor.com # EPS10 Series Alarm Pressure Switches ## Specifications | Contact Ratings: | 10 A, 1/2 HP @ 125/250 VAC<br/>2.5A @ 6/12/24 VDC | | ---------------------------- | ---------------------------------------------------------------- | | Overall Dimensions: | Se

> **evidencia 2** (chunk_index 4): ## Figure 3. Switch terminals: [Diagram showing switch terminal assembly with the following labeled components:] - SWITCH #1 (top switch assembly) - COMMON TERMINALS - TERMINAL "A" - SWITCH #2 (second switch assembly) - TERMINAL "B" - GROUND SCREW (bottom left) - LOCKING SCREW (bottom center) [Bottom view showing four terminal connection blocks arranged in a 2x2 grid] BREAK WIRE AS SHOWN FOR SUPERVISION OF CONNECTION

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 16. `bc0c7b5f-95f7-4198-806c-b17dac41d32e` — propuesta: **es**

- stem: `TIDT110`
- fichero: `TIDT110.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 17, 'es': 63, 'fr': 0, 'it': 3, 'pt': 3}` · 2º idioma: `en` (17) · margen: 3.706x · chunks muestreados: 6

> **evidencia 1** (chunk_index 0): Honeywell **Información técnica** **TI-DT-110** **22/03/2010** # **NOTIFIER®** # **Convertidor RS232 a RS485/422 para TG a centrales ID3000 - punto a punto. Ref.: CONV232/485** Las conexiones de puerto serie RS-232 no están aconsejadas para longitudes de cableado superiores a 15/20 metros. Cuando existan caídas de tensión debidas a las longitudes del cable, es posible instalar convertidores de RS-232 a RS-485/422 en 

> **evidencia 2** (chunk_index 3): ## 2. Conexionado de la placa RS-232 del panel ID50/60 al convertidor Extremo A | Cable de placa RS-232 a Convertidor Extremo A | Cable de placa RS-232 a Convertidor Extremo A | | --------------------------------------------- | --------------------------------------------- | | Placa RS-232 en ID3000 | D-Sub-9/M Convertidor | | Rx PIN 3 | 2 (Tx) | | Tx PIN 2 | 3 (Rx) | | GND PIN 5 | 5 (GND) | **Selección de Interrupto

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 17. `09194202-db14-4299-867f-143d02267601` — propuesta: **en**

- stem: `3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet`
- fichero: `3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet.pdf` · marca: Kidde
- marcadores por idioma: `{'en': 217, 'es': 1, 'fr': 0, 'it': 0, 'pt': 2}` · 2º idioma: `pt` (2) · margen: 108.5x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # KIDDE **COMMERCIAL** # Excellence Series Intelligent Addressable Indoor Notification Device Installation Sheet EN DE ES FR IT NL PL PT **1** [Diagram 1: Circular device front view showing: (1) VAD/VID lens - circular center area (2) Status LED - small rectangular element on the right side of the device] **2** [Diagram 2: Circular device back view showing internal mounting base with multiple terminal connections arr

> **evidencia 2** (chunk_index 5): ## Device status The device status is indicated by the status LED, as shown in the table below. | State | Indication | | ------------------- | ------------------- | | Isolation active | Steady yellow LED | | Device fault | Flashing yellow LED | | Located device \[1] | Steady green LED | | Communicating \[2] | Flashing green LED | [1] Indicates an active Locate Device command from the control panel. [2] This indicatio

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 18. `217117c0-5b56-4225-9734-e600e5c4d8c7` — propuesta: **es**

- stem: `MADT212`
- fichero: `MADT212` · marca: Notifier
- marcadores por idioma: `{'en': 12, 'es': 206, 'fr': 18, 'it': 21, 'pt': 32}` · 2º idioma: `pt` (32) · margen: 6.438x · chunks muestreados: 6

> **evidencia 1** (chunk_index 0): **NOTIFIER ESPAÑA, S.A.** **Avda Conflent 84, nave 23** **Pol. Ind. Pomar de Dalt** **08916 Badalona (Barcelona)** **Tel.: 93 497 39 60; Fax: 93 465 86 35** # SUPLEMENTO DEL MANUAL DE INSTALACIÓN DE LA CENTRAL DE ALARMA CONTRA INCENDIOS SERIE ID1000 [Image shows a NOTIFIER ID1000 fire alarm control panel mounted in a black cabinet. The panel features a display screen at the top, multiple indicator LEDs arranged in ro

> **evidencia 2** (chunk_index 3): MA-DT-212 NOTIFIER ESPAÑA, S.A. 2 de 3 # Instalar/Reemplazar la tarjeta de lazo TX, Ref. 124-065 Para instalar la Tarjeta de lazo TX en su panel de la Serie 1000 siga el procedimiento de la Fase 1 descrito a continuación y en la Fase 2 en la página 3. Para reemplazar la tarjeta de lazo TX realice el procedimiento inverso descrito en la página 3. | **Fase 1 - Instalación de la placa** | Tome las precauciones adecuadas

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 19. `f5224079-3c15-421a-83fe-5506edbc3100` — propuesta: **en**

- stem: `04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0`
- fichero: `04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 343, 'es': 4, 'fr': 1, 'it': 0, 'pt': 14}` · 2º idioma: `pt` (14) · margen: 24.5x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): [AirSense logo with stylized "A" in a square and starburst design] # Aritech APIC Installation Sheet for ModuLaser Aspirating Smoke Detection Systems **1** [Diagram of a circuit board showing various components including connectors on the left side, empty spaces in the center, and a multi-pin connector on the right side] **2** | SW1 | SW2 | SW3 | | ------------------------------------ | ------------------------------

> **evidencia 2** (chunk_index 5): ## Interface details Analogue values for device status are shown in the table below. | Value | Status | | ----- | --------------------------------------------------- | | 1 | General Fault | | 2 | Flow/Filter Fault | | 3 | Disabled | | 4 | Internal APIC Fault (Hardware) | | 5 | Internal APIC Fault (Data Corruption) | | 6 | Internal APIC Fault (Parallel Comms – Ribbon Cable) | | 7 | Internal APIC Fault (Watchdog) | | 8

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 20. `0ad0a70f-f97b-4f88-90ff-65fad585ce51` — propuesta: **es**

- stem: `MA-AL-T500-01-07 Manual TUL500esp rev1`
- fichero: `MA-AL-T500-01-07 Manual TUL500esp rev1` · marca: Venitem
- marcadores por idioma: `{'en': 21, 'es': 195, 'fr': 12, 'it': 35, 'pt': 31}` · 2º idioma: `it` (35) · margen: 5.571x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): VENITEM # FUENTE DE ALIMENTACIÓN TUL500EN **CERTIFICADA con las normas EN 54-4:1997+A1:2002+A2:2006 EN 12101-10:2005** ## Manual de instalación ## CARACTERISTICAS GENERALES La Fuente de alimentación TUL500EN ha sido diseñada para ser utilizada como como una unidad de alimentación con Fuente de reserve para sistemas de detección y alarma de incendios, en conformidad con la regulación (EU) No 305/2011 y como equipo de 

> **evidencia 2** (chunk_index 5): ## Tipos y secciones recomendados de cables de instalación (certified EN50200) | Alimentación principañ 230 V\~ L-N-PE | FTG10OM1 0,6/1 kV: 3 x 1,5 mm²÷2,0 mm² | | ------------------------------------- | -------------------------------------- | | Terminales de salida A, B, C | FRHRRNS 2150: 2 x 1,5 mm²÷2,0 mm² | | Indicación entradas/Salidas | FRHRRNS 2050: 2 x 0,5 mm²÷1,5 mm² | Tab 4 **La fuente de alimentación ha s

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 21. `43cabec0-500c-4b2b-95a9-0cc2cda98101` — propuesta: **en**

- stem: `I56-5002-000-Morley-Strobe`
- fichero: `I56-5002-000-Morley-Strobe` · marca: Morley
- marcadores por idioma: `{'en': 101, 'es': 33, 'fr': 29, 'it': 23, 'pt': 9}` · 2º idioma: `es` (33) · margen: 3.061x · chunks muestreados: 5

> **evidencia 1** (chunk_index 0): Estos dispositivos solo deben conectarse a paneles de control que utilicen un protocolo de comunicación direccionable analógico compatible y propio. Estos dispositivos reciben su energía del lazo y pueden controlarse a través de los protocolos de comunicación. Nota: Si el equipo de control no es capaz de tomar más de 99 direcciones de módulo, se generará un fallo por cada dirección que supere a la dirección 99. Para 

> **evidencia 2** (chunk_index 2): ## <ins>ANTI TAMPER RELEASE</ins> [Icon showing a lock] **(ENG) IMPORTANT:** Follow the instruction strictly: 1) Insert a flat screwdriver 2) Lever the screwdriver down and twist the device anticlockwise. 3) Remove the screwdriver to unlock the device. **(FRE) IMPORTANT:** Suivez strictement les instructions : 1) Insérez un tournevis plat 2) Faites descendre le tournevis et tournez le dispositif dans le sens inverse 

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 22. `4112c5c1-0362-407e-8713-bbd4e3fcbf9a` — propuesta: **es**

- stem: `MIE-MA-300_01`
- fichero: `MIE-MA-300_01.pdf` · marca: Morley
- marcadores por idioma: `{'en': 3, 'es': 317, 'fr': 27, 'it': 41, 'pt': 70}` · 2º idioma: `pt` (70) · margen: 4.529x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): MORLEY IAS FIRE SYSTEMS Morley-IAS Av.Industria,32 Bis. Posterior local 1 - Nave 2 P.I. Alcobendas 28108 - Madrid # <ins>ANEXO I</ins> al Manual MIE-MI-300 de la central analógica contra incendios ZX50 para la versión 5.02 con control de extinciones e integración. [Yellow triangle warning symbol with exclamation mark] ## NOTAS IMPORTANTES ∑ Cualquier operación de carga y descarga con la versión de software **5.02** d

> **evidencia 2** (chunk_index 5): **EXS**. Relé de lazo de Extinción. Salida supervisada. Tipo de ID para módulos de control MI-CME para **sistema de extinción**. No se activa con las pruebas del sistema y permite ser anulado al anular los sistemas de extinción. Controla la línea de (En este caso solo se conectará la salida del módulo la resistencia final de línea de 47KW para la supervisión de la línea). MIE-MA-300_01A; 24/05/04 Morley-IAS ESPAÑA 5 

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 23. `fc3d273e-7f99-402a-99e4-9099d8cefe8e` — propuesta: **en**  ⚠️ **PISTA MULTI-IDIOMA en el nombre: `['gb', 'it', 'ru']`**

- stem: `085501945t_PA5_Installation_manual_D-GB-F-RU-IT`
- fichero: `085501945t_PA5_Installation_manual_D-GB-F-RU-IT` · marca: Pfannenberg
- marcadores por idioma: `{'en': 407, 'es': 0, 'fr': 2, 'it': 0, 'pt': 5}` · 2º idioma: `pt` (5) · margen: 81.4x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): 085 501 945t 30304-004t 1 # PA 5 / PA X 5-05/ PA X 5-10 - Betriebs- und Montageanleitung ## Maße **PA 5** Technical drawing showing three views: - Front view: Square housing 163.4 [6.43"] wide × Ø73 [Ø2.87"] high, with circular speaker grille in center, four mounting holes at corners. Dimensions: 37 [1.46"] from edge, 143 [5.63"] between mounting holes - Side view: Depth 132 [5.2"], showing M20-Ausbruch vorbereitet (

> **evidencia 2** (chunk_index 5): # Approvals | Approvals (valid for marked equipment) | Approvals (valid for marked equipment) | Approvals (valid for marked equipment) | Approvals (valid for marked equipment) | | | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 24. `0dde8e85-4d91-4916-8c27-d3981fc564ca` — propuesta: **es**

- stem: `MIE-MC-130rv02`
- fichero: `MIE-MC-130rv02.pdf` · marca: Morley
- marcadores por idioma: `{'en': 21, 'es': 295, 'fr': 32, 'it': 38, 'pt': 35}` · 2º idioma: `it` (38) · margen: 7.763x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): MORLEY IAS FIRE SYSTEMS by Honeywell MK-VSN Documento No.MIE-MC-130rv002 Manual de Funcionamiento MORLEY-IAS MK-VSN Serie VISION Plus # Índice **1 INTRODUCCIÓN......................................................................................................................... 3** 1.1 AVISO .............................................................................................................................

> **evidencia 2** (chunk_index 5): # 4 Iniciar el Programa MK-VSN Una vez instalado el programa en su disco duro. Acceda a la carpeta donde haya copiado los archivos del programa y haga doble clic sobre el archivo **VSN.exe** o sobre el acceso directo del escritorio, si lo ha creado, para iniciar el programa de configuración MK-VSN. [MKVSN folder icon with file listing showing: USUARIO.DAT, VBRUN300.DLL, VSN.EXE, VSN.HLP. Text reads "Seleccione un ele

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 25. `c295d7f9-f137-4ce4-96a6-d3fda323ba5c` — propuesta: **en**

- stem: `MNDT960I`
- fichero: `MNDT960I.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 274, 'es': 0, 'fr': 0, 'it': 0, 'pt': 5}` · 2º idioma: `pt` (5) · margen: 54.8x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): NOTIFIER® FIRE SYSTEMS NOTIFIER ESPAÑA, S.A. Central: Avda. Conflent 84, Nave 23 Pol. Ind. Pomar de Dalt 08916 BADALONA (BARCELONA) Tel.: 93 497 39 60 Fax: 93 465 86 35 # POLLING BOARD # *POL-1* PRELIMINARY COPY # User Manual **MN-DT-9601 13 OCTOBER 2000** *All specifications are subject to change without notice* # POL-1 Instructions Manual ## <ins>Configuration Screen</ins> | \*\*Serial Port Configuration\*\* | | | 

> **evidencia 2** (chunk_index 5): ## Selecting devices Up to 20 devices can be monitored in the selected sequence by clicking on the check button ``` ┌────────────────────────────────────────┐ │ 02 ☑ │ └────────────────────────────────────────┘ ``` ``` ┌──┬───┬───┬───┬───┬──┬──┬──┬──┬───┐ │1 │26 │27 │29 │31 │2 │3 │4 │1 │42 │ ├──┼───┼───┼───┼───┼───┼──┼──┼───┼───┤ │41│50 │8 │105│106│107│2 │1 │16 │108│ └──┴───┴───┴───┴───┴───┴──┴──┴───┴───┘ 2 sec. ┌──┬

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 26. `d1299a40-5128-464d-b8d7-1c8c2b86562c` — propuesta: **es**

- stem: `DXc_Manual de configuracion`
- fichero: `DXc_Manual de configuracion` · marca: Morley
- marcadores por idioma: `{'en': 24, 'es': 245, 'fr': 15, 'it': 31, 'pt': 33}` · 2º idioma: `pt` (33) · margen: 7.424x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): Honeywell | Fire Safety DX CONNEXION™ # Manual de configuración - PÁGINA 2 - # DX CONNEXION™ Manual de configuración # Índice | Sección | Título | Página | | --------- | ------------------------------------------------------ | ------ | | 1 | Introducción | 4 | | 1.1 | Avisos | 4 | | 1.2 | Modelos | 1 | | 1.3 | Advertencias y precauciones | 5 | | 1.4 | Requisitos nacionales | 6 | | 1.5 | Información EN54 | 4 | | 2 | D

> **evidencia 2** (chunk_index 5): ## 1.4 Requisitos nacionales * Este equipo debe instalarse siguiendo estas instrucciones y la normativa nacional y local aplicable. Consulte a la autoridad competente para confirmar dichos requerimientos. ---- **Todo el equipamiento debe instalarse de acuerdo a los requisitos nacionales y locales del lugar donde va a ser instalado.** ---- ## 1.5 Información EN54 Esta central de alarma contra incendios cumple los requ

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 27. `3138edc4-6974-4a66-9357-02a10c60c46d` — propuesta: **en**

- stem: `I56-2956-000_prelim`
- fichero: `I56-2956-000_prelim.pdf` · marca: Morley
- marcadores por idioma: `{'en': 435, 'es': 53, 'fr': 7, 'it': 19, 'pt': 10}` · 2º idioma: `es` (53) · margen: 8.208x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): INSTALLATION AND MAINTENANCE INSTRUCTIONS MORLEY IAS FIRE SYSTEMS by Honeywell I56-2956-000 # MI-SC6 # Six Supervised Control Module Morley IAS Fire Systems Charles Avenue Burgess Hill, West Sussex, RH15 9UF ## SPECIFICATIONS Normal Operating Voltage: 15-32VDC Stand-By Current: 2.25 mA Alarm Current: 35 mA (assumes all six relays have been switched once and all six LEDs solid on) Temperature Range: -10°C to 55°C Humi

> **evidencia 2** (chunk_index 5): | **Circuit Components (Left Side):** | | | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | | 47K Resistor | Connected between terminals | | EOL Relay Connections | RED (–), BLK (–), with 47K resistor<br/>(+), (+) connections to VIO | | External 

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 28. `a107427f-5534-406b-b153-98c6e08e4524` — propuesta: **es**

- stem: `Manual Testifire_Spanish`
- fichero: `Manual Testifire_Spanish` · marca: Xtralis
- marcadores por idioma: `{'en': 43, 'es': 324, 'fr': 30, 'it': 27, 'pt': 71}` · 2º idioma: `pt` (71) · margen: 4.563x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # testifire® COMPROBADOR DE DETECTOR MULTIESTÍMULO # Manual del usuario [Large product image showing the Testifire 2000 device - a white and gray cylindrical testing unit with a white dome top, clear chamber in the middle, and a handheld remote control unit attached. The remote has a digital display showing "Paper Detected" and multiple control buttons including green buttons, directional pad, and red power button. T

> **evidencia 2** (chunk_index 5): # Índice | | | N.° de página | | ------ | ------------------------------------------------------------------------------- | ------------- | | **1.** | **Instrucciones generales** | 4 | | | 1.1 Garantía | 4 | | | 1.2 Reconocimiento | 4 | | | 1.3 Reciclado | 4 | | **2.** | **Introducción** | 5 | | **3.** | **Identificación de piezas** | 6 | | **4.** | **Funcionamiento básico del equipo** | 7 | | | 4.1 Recargar las Bate

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 29. `be1b6b42-721f-442f-a453-477a5e4dc795` — propuesta: **en**

- stem: `MNDT960I_iBox-BACnet`
- fichero: `MNDT960I_iBox-BACnet` · marca: Notifier
- marcadores por idioma: `{'en': 189, 'es': 2, 'fr': 0, 'it': 3, 'pt': 7}` · 2º idioma: `pt` (7) · margen: 27.0x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): **Honeywell Life Safety Iberia** C/Pau Vila 15-19 08911 Badalona (Barcelona) Tel.: 902 03 05 45 www.honeywelllifesafety.es www.notifier.es | infonlsiberia@honeywell.com # iBox BACnet/IP Gateway for the integration of Notifier ID3000 and Morley DXc fire panel series in BACnet/IP enabled monitoring and control systems. *User Manual* **MN-DT-960I 27 FEBRUARY 2013** (IBOX-BAC-NID3000 / r1 eng) *Information in this docume

> **evidencia 2** (chunk_index 5): | Element | Object supported | | -------- | ---------------------- | | Detector | • Status<br/>• Command | | Module | • Level | | Zone | • Status<br/>• Command | ## 1.3 *Capacity of iBox* iBox is capable of integrating one single Notifier ID3000 panel and its associated elements. | Element | Max. | Notes | | ----------------- | ---- | -----------------------------------------------------------------------------------

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 30. `7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6` — propuesta: **es**

- stem: `MNDT1025`
- fichero: `MNDT1025` · marca: Notifier
- marcadores por idioma: `{'en': 2, 'es': 330, 'fr': 43, 'it': 47, 'pt': 88}` · 2º idioma: `pt` (88) · margen: 3.75x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): **NOTIFIER®** **FIRE SYSTEMS** Grupo **Honeywell** NOTIFIER ESPAÑA, S.L. Avda Conflent 84, nave 23 Pol. Ind. Pomar de Dalt 08916 Badalona (Barcelona) Tel.: 93 497 39 60; Fax: 93 465 86 35 # Detector de humo analógico con cámara láser VIEW # Aplicaciones del VIEW™ **MN-DT-1025** **8 ABRIL 2004** **(doc. 997-198)** *Toda la información contenida en este documento puede ser modificada sin previo aviso.* MN-DT-1025 NOFIF

> **evidencia 2** (chunk_index 5): Como segunda ventaja, la cooperación entre sensores ofrece una respuesta más rápida ante verdaderos incendios que los sistemas en los que no existe tal cooperación. Como parte de los algoritmos AWACS, las señales procedentes de los sensores adyacentes se combinan de manera sofisticada para alcanzar una señal común. Por lo tanto, el VIEW puede indicar una condición de alarma antes de que la señal procedente de cualqui

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

**Recuento final:** ____ / 30 correctos. 30/30 -> gate (e)(iii) verde. Cualquier fallo -> HALT.
