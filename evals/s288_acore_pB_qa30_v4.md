# s288 A-CORE — packet QA-30 de P-B para adjudicacion — v4

**Que hay que decidir (spec F0(e)(iii)):** para cada documento, ¿el idioma PROPUESTO es el idioma del documento? Regla de aceptacion: **30/30 correctos -> gate (e) verde; cualquier fallo -> HALT y revision del detector** (y, si el fallo es de un label legacy, revision de la cohorte etiquetada — spec riesgo 8). Marca `[x] OK` o `[x] MAL` por ficha.

**Los extractos estan LIMPIOS de anotaciones del extractor** (spans `[...]` en ingles describiendo figuras: «[Diagram showing…]»). Es lo que el detector cuenta, y evita adjudicar sobre texto que no es del documento.

- cohorte P-B (activos, `language IS NULL`, detector v2 confianza alta): **406** documentos · `{'en': 99, 'es': 307}`
- muestra: **30** documentos, estratificada por idioma propuesto, round-robin determinista sobre `md5(document_id)`
- detector: **v3_endurecido_fix1_fix2_fix3** · muestra 10 chunks/doc · alta ⇔ >=20 marcadores Y >=2.0x el segundo, + supresion de token dominante (>50%) + cruce de familia >= 3.0x + limpieza de anotaciones del extractor `[...]`
- freeze: commit `3437c38ea004` · corpus sha `744f21af87de1df9` · determinismo 2x OK

**Aviso de honestidad:** el detector NO es fiable fuera de {es, en} (todos los labels `it`/`fr`/`pt`/`nl` del corpus se detectan como `en`). Si alguna ficha propone un idioma distinto de `es`/`en`, trata la propuesta como sospechosa por defecto.

**Blind spot declarado:** el FIX 2 solo degrada cuando el 2º idioma cruza familia (`en` vs romance); un documento realmente mixto **es+fr/it/pt** NO se degrada. Como ayuda, las fichas cuyo NOMBRE sugiere multi-idioma llevan la marca ⚠️ **PISTA MULTI-IDIOMA** (heuristica de nombre, ADVISORY, no entra en ningun veredicto): **2 de 30** fichas.

---

## 1. `65669851-7431-412f-b727-bd65af27a170` — propuesta: **en**

- stem: `MNDT951I`
- fichero: `MNDT951I.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 627, 'es': 1, 'fr': 0, 'it': 1, 'pt': 3}` · 2º idioma: `pt` (3) · margen: 209.0x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): *TG - NOTIFIER* *USER'S GUIDE* *MN-DT-951I (Rev.: 5.83) December 2004* USER'S GUIDE INDEX # <ins>SUBJECTS INDEX</ins> 1. INTRODUCTION ............................................................... <ins>1</ins> 1.1. Basic concepts ........................................................ <ins>3</ins> 1.2. The keyboard and the mouse ............................................. <ins>4</ins> 1.2.1. The keyboard ........

> **evidencia 2** (chunk_index 5, 4 anotacion(es) del extractor eliminadas): # NOTIFIER FIRE SYSTEMS (this key is usually labelled Esc and is placed in the top left side of the keyboard). * *To type* means that you must enter specific data. For instance, if you are told to type "C:\", you should press the keys corresponding to these given characters in the keyboard. * *To enter*. This general term will always refer to information that cannot be expressed with precise instructions. For instanc

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 2. `f1a60b0d-54af-42eb-bb25-d999a174336f` — propuesta: **es**  ⚠️ **PISTA MULTI-IDIOMA en el nombre: `['es', 'fr', 'gb', 'it']`**

- stem: `55350005 Manual Central Monoxido CMD-500 ES FR GB IT`
- fichero: `55350005 Manual Central Monoxido CMD-500 ES FR GB IT` · marca: Detnov
- marcadores por idioma: `{'en': 4, 'es': 381, 'fr': 40, 'it': 47, 'pt': 67}` · 2º idioma: `pt` (67) · margen: 5.687x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # GUIDE MANUAL ES GB FR IT *Monoxide control panels User's and installation guide* NO_CONTENT_HERE # MANUAL DEL USUARIO ES *Centrales de detección de monóxido* *Guía de instalación y usuario* NO_CONTENT_HERE # ÍNDICE 1- Introducción.............................................................................................................5 **1.1- Descripción General de la Serie.......................................

> **evidencia 2** (chunk_index 5, 1 anotacion(es) del extractor eliminadas): ## 2.5- Conexión baterías ### (Opcional. Necesita modulo) Las centrales de monóxido requieren dos baterías de 12V el alojamiento esta preparado para baterías de 12V 2.3A/h y para baterías de 12V 7A/h. Las baterías deben conectarse en serie para el correcto funcionamiento de las centrales. El cable que se suministra con la central debe conectarse de forma que una el polo positivo de una batería con el polo negativo de

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 3. `84365c09-608f-4b5e-abc3-ff610a7acd41` — propuesta: **en**

- stem: `00-3280-507-4003-03_r003_2x-a_series_quick_installation_guide_en`
- fichero: `00-3280-507-4003-03_r003_2x-a_series_quick_installation_guide_en.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 201, 'es': 0, 'fr': 0, 'it': 1, 'pt': 4}` · 2º idioma: `pt` (4) · margen: 50.25x · chunks muestreados: 4

> **evidencia 1** (chunk_index 0): KIDDE COMMERCIAL # 2X-A Series Quick Installation Guide ## Overview This document includes quick installation information for your 2X-A control panel. For detailed installation information (including EN 54-13 requirements) and for configuration options, see the product installation manual. **WARNING:** Electrocution hazard. To avoid personal injury or death from electrocution, remove all sources of power and allow st

> **evidencia 2** (chunk_index 2): # Overview of typical fire system connections using a single Class A loop [Technical diagram showing a fire system connection schematic with the following components and labels: - Top section: A loop circuit with circular symbols (detectors), a butterfly valve symbol, and rectangular boxes connected in series - Middle section: Three vertical panels with multiple connection points, showing 15 kΩ resistors at various l

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 4. `0426c906-5080-499a-afb3-f45766907458` — propuesta: **es**

- stem: `HLSI-MN-963_POL-200-TS`
- fichero: `HLSI-MN-963_POL-200-TS` · marca: Morley
- marcadores por idioma: `{'en': 1, 'es': 247, 'fr': 24, 'it': 21, 'pt': 40}` · 2º idioma: `pt` (40) · margen: 6.175x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): Honeywell | Manual de usuario # POL-200-TS ## HERRAMIENTA DE DIAGNÓSTICO DEL LAZO POL-200-TS Manual de Usuario # Información de seguridad ⚠️ **¡Importante!:** *Antes de conectar cualquier cable externo, compruebe que el cable de lazo NO está conectado a la central por ninguno de los dos extremos del lazo.* Compruebe la correcta conexión de los terminales y que no existe ninguna tensión externa entre los cables que se

> **evidencia 2** (chunk_index 5): # 4. Lazo POL-200-TS device La herramienta reconoce los detectores y los módulos en el lazo, no es necesario conectarlo al panel de detección (FACP). El POL-200-TS es compatible con el protocolo CLIP diseñado para gestionar 99 detectores y 99 módulos en el lazo y también con el Protocolo Avanzado diseñado para gestionar 159 detectores y 159 módulos. En el menú **auto-programación**, nos identificará el número de dete

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 5. `f763235d-17dc-477e-b736-d45571c7f992` — propuesta: **en**

- stem: `WFDEN_Manual_I56-4051`
- fichero: `WFDEN_Manual_I56-4051` · marca: System Sensor
- marcadores por idioma: `{'en': 336, 'es': 5, 'fr': 1, 'it': 0, 'pt': 13}` · 2º idioma: `pt` (13) · margen: 25.846x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): I56-4051-003R # INSTALLATION AND MAINTENANCE INSTRUCTIONS System Sensor Logo 3825 Ohio Avenue, St. Charles, Illinois 60174 1-800-SENSOR2, FAX: 630-377-6495 www.systemsensor.com # WFDEN Vane-type Water flow Detector ## SPECIFICATIONS Contact Ratings: 10 A @ 125/250 VAC ~ ; 2.5 A @ 24 VDC ⚌ Triggering Flow Rate: Refer to Table 1 Static Pressure Rating (maximum): 17.25 bar (250 psi) (1725 KPa); 16 bar (VdS) Operating Te

> **evidencia 2** (chunk_index 5, 3 anotacion(es) del extractor eliminadas): ## FIGURE 1. MOUNTING DIMENSIONS: ## FIGURE 2. LOCATION OF MOUNTING HOLE TOP VIEW: INCORRECTO CORRECTO QUITE LAS REBABAS DEL EXTREMO DEL ORIFICIO. LIMPIE EL ÓXIDO Y LOS RESIDUOS DE LA PARED INTERIOR DE LA TUBERÍA. W0106-00

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 6. `bc163277-ad9e-4ced-950f-c0e63de35a0a` — propuesta: **es**

- stem: `55310600 Manual TCD-106 kit_ES`
- fichero: `55310600 Manual TCD-106 kit_ES` · marca: Detnov
- marcadores por idioma: `{'en': 26, 'es': 205, 'fr': 12, 'it': 44, 'pt': 21}` · 2º idioma: `it` (44) · margen: 4.659x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MANUAL DEL INSTALADOR ES *Manual kit transmisión CRA* NO_CONTENT_HERE 3 # Índice **1-Instalación sistema convencional** ........................................................ 4 1.1- introducción....................................................................................... 4 1.2- Montaje tarjeta conexión .................................................................. 4 1.3- Conexionado e Instalación 5 

> **evidencia 2** (chunk_index 5, 1 anotacion(es) del extractor eliminadas): El cableado entre la tarjeta de conexión y el módulo de transmisión debe hacerse desde los terminales A y B de la salida MODBUS de la tarjeta hasta los terminales B y A del módulo. Para equilibrar la impedancia de la línea, es necesario conectar una resistencia de 120Ω en la bornera de la tarjeta de conexión. Además, el módulo de transmisión debe alimentarse a una tensión comprendida entre 12 Vdc y 30 Vdc a través de

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 7. `f8132ff7-ef29-478e-8304-c94e60fd4288` — propuesta: **en**

- stem: `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_panel_compatibility_list_900_series_protocol`
- fichero: `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_panel_compatibility_list_900_series_protocol.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 137, 'es': 0, 'fr': 3, 'it': 0, 'pt': 2}` · 2º idioma: `fr` (3) · margen: 45.667x · chunks muestreados: 8

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): KIDDE COMMERCIAL # 2X-A and ZP2-A Series Addressable Control Panel Compatibility List (900 Series Protocol) ## Introduction This document lists the products compatible for use with 2X-A and ZP2-A Series fire alarm control panels (firmware 4.x only) when using the 900 Series protocol. **WARNING:** Only those devices included in this publication are tested and confirmed compatible for use with 2X-A and ZP2-A Series fir

> **evidencia 2** (chunk_index 4): | Device range | Model | Description | Notes | | ------------------------------------ | --------------- | ------------------------------------------------------------------------------ | ----------------------------------------- | | 950 Series Notification | AS967WRCI\* | Apollo XP95 Loop-powered open area sounder/VID with isolator (clear lens) | | | 950 Series Notification | DB952IAS\* | Apollo XP95 85/92 dB integra

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 8. `123dc496-4b91-43a5-8855-c3998ed20d37` — propuesta: **es**

- stem: `MIE-MC-530`
- fichero: `MIE-MC-530.pdf` · marca: Morley
- marcadores por idioma: `{'en': 29, 'es': 328, 'fr': 17, 'it': 44, 'pt': 43}` · 2º idioma: `it` (44) · margen: 7.455x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): MORLEY IAS FIRE SYSTEMS by Honeywell # MK-ZX Documento No.MIE-MC-530rv001 Manual de Funcionamiento MORLEY-IAS Fire6 Serie ZX # Índice **1 INTRODUCCIÓN......................................................................................................................... 3** 1.1 AVISO .................................................................................................................................... 3

> **evidencia 2** (chunk_index 5, 4 anotacion(es) del extractor eliminadas): # 3 Instalación del Programa Fire6 El programa se entrega en soporte óptico totalmente instalado. Abra el Explorador de Windows y seleccione la unidad de lector de Discos de su PC (CD) donde haya insertado el disco del Fire6, haciendo doble clic sobre ésta con el botón izquierdo del ratón. Se mostrarán los archivos que contiene el disco. -Seleccione todos los archivos, desde **Edición** del Explorador de Windows, hac

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 9. `aac0d826-9830-4f6e-a9a8-dc0159bffee7` — propuesta: **en**

- stem: `10-5106-501-55nc-05_r005_iu2055nc_installation_sheet_ml`
- fichero: `10-5106-501-55nc-05_r005_iu2055nc_installation_sheet_ml.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 285, 'es': 59, 'fr': 6, 'it': 8, 'pt': 12}` · 2º idioma: `es` (59) · margen: 4.831x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): # aritech # IU2055NC Conventional Zone Monitor Unit Installation Sheet EN DA ES FR HU IT LT NL PL PT RO SV TR ## 1 ## 2 J5 (5) 5 6 7 8 9 3 4 5 6 4 2 10 2 7 2 1 11 1 8 1 0 12 0 9 J4 (6) COM2 COM1 IND (4) \+ + - \+ - DET+ DET- (3) (1) + (2) (7) © 2025 Kidde Commercial. All rights reserved. 1 / 32 P/N 10-5106-501-55NC-05 • REV 005 • 29MAY25 # 3

> **evidencia 2** (chunk_index 5): # Specifications | Device operating voltage | 21 to 28 VDC | | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | | Device current consumption<br/>Standby<br/>Alarm | <br/>< 15 mA<br/>< 40 mA | | Remote LED current | 3.6 mA | | Zone operating voltage (in standby) | 17.5 to 18.5 VDC | | Zone cable resistance<b

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 10. `08828182-830a-4776-a6c4-32ab605c4665` — propuesta: **es**

- stem: `MIE-MI-010`
- fichero: `MIE-MI-010.pdf` · marca: Morley
- marcadores por idioma: `{'en': 8, 'es': 306, 'fr': 26, 'it': 39, 'pt': 65}` · 2º idioma: `pt` (65) · margen: 4.708x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 7 anotacion(es) del extractor eliminadas): # MORLEY IAS ## FIRE SYSTEMS ### by Honeywell # MPS Documento No.MIE-MI-010rv002 # Manual de Instalación www.morley-ias.es # INSTRUCCIONES IMPORTANTES DE SEGURIDAD ## Medidas de seguridad • No levante cargas pesadas sin ayuda | => < 18 Kg | \ | => 32 - 55 Kg | \ | | ------------- | ------------------------------ | ------------- | -------------------------------------- | | => 18 - 32 Kg | \ | => > 55 Kg | \ | • No uti

> **evidencia 2** (chunk_index 5): # Características de las fuentes de alimentación MPS15, MPS25, MPS50. Las fuentes de alimentación (F.A.) de Morley-IAS MPS15, MPS25 y MPS50 se han diseñado cumpliendo los criterios de la norma EN54-4 con el fin de suministrar alimentación de apoyo a sistemas de control de incendio. Revise la reglamentación vigente para una correcta instalación de la misma y de los circuitos y equipos que desee alimentar. Todos los ca

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 11. `637cc4d7-9e96-4545-9202-d6cb3463e701` — propuesta: **en**

- stem: `2x-at-f2-fb-p-161721-es`
- fichero: `2x-at-f2-fb-p-161721-es.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 133, 'es': 15, 'fr': 1, 'it': 4, 'pt': 1}` · 2º idioma: `es` (15) · margen: 8.867x · chunks muestreados: 5

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): KIDDE COMMERCIAL # 2X-AT-F2-FB-P **Addressable fire panel with tocuhscreen fire brigade controls, 2 loop, with bigger PSU** ## Overview The new 2X-A series life safety control systems bring the speed and functionality of high-end intelligent processing to small to mid-sized addressable applications. Based on 2X series learned experience and with complete backwards compatibility, the new 2X-A features an attractive co

> **evidencia 2** (chunk_index 2): # 2X-AT-F2-FB-P **Addressable fire panel with tocuhscreen fire brigade controls, 2 loop, with bigger PSU** ## Especificaciones técnicas ### General | Interfaz usuario | Con controles de Bomberos | | ----------------------------------------------------- | ------------------------- | | Capacidad máxima del sistema (número de dispositivos) | hasta 32512 | | Tamaño de la red (nodos) | hasta 64 | ### Eléctrico | Tipo de f

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 12. `0e9330c8-2c53-4941-bf4f-17fe40adbe84` — propuesta: **es**

- stem: `MIE-MI-530rv001`
- fichero: `MIE-MI-530rv001` · marca: Morley
- marcadores por idioma: `{'en': 1, 'es': 120, 'fr': 9, 'it': 16, 'pt': 16}` · 2º idioma: `it` (16) · margen: 7.5x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MORLEY IAS # FIRE SYSTEMS ## by Honeywell # ZX2e # ZX5e Documento No.MIE-MI-530 rev.001 # manual de instalación **manual para el instalador.** MORLEY-IAS Paneles de Incendio ZX2e / ZX5e # Índice ## 1 INTRODUCCIÓN......................................................................................................................... 5 1.1 AVISO ........................................................................

> **evidencia 2** (chunk_index 5): ## Índice de Tablas TABLA 1 – CONTENIDO.......................................................................................................................... 8 TABLA 2 – LONGITUDES TÍPICAS RECOMENDADAS................................................................................. 17 TABLA 3 – LISTA DE EQUIPOS PERIFÉRICOS COMPATIBLES .................................................................... 26 TABLA 4

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 13. `c96bb93b-115e-42ef-920d-56a00201861c` — propuesta: **en**

- stem: `I56-3888-010 FAAST LT-200 Adv Guide`
- fichero: `I56-3888-010 FAAST LT-200 Adv Guide` · marca: Xtralis
- marcadores por idioma: `{'en': 313, 'es': 0, 'fr': 0, 'it': 0, 'pt': 3}` · 2º idioma: `pt` (3) · margen: 104.333x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # FAAST LT-200 ## FIRE ALARM ASPIRATION SENSING TECHNOLOGY® ## ADVANCED SET-UP AND CONTROL GUIDE ## CONTENTS | Introduction. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1 | Further PipeIQ™ Capabilities. . . . . . . . . . . . . . . . . . . . . . . . . . . 5 | | | | ------------------------------------------------------------------------------------------------- | -----------------

> **evidencia 2** (chunk_index 5): ## <ins>Service Mode</ins> When the FAAST LT-200 device is in *Normal*, the *Service Mode* state is entered automatically when the front cover is opened. The FAAST LT-200 unit switches off the power to the unit. Once the service action is complete, and the front cover is closed, the FAAST LT-200 device restarts automatically. Note that when leaving *Service Mode*, a unit will always run the initialise routine, re-cal

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 14. `a2bb8ee1-b20b-4f20-9a72-a59f6f560a0a` — propuesta: **es**

- stem: `Conexionado-del-modulo-M710-CZ-MI-DCZM`
- fichero: `Conexionado-del-modulo-M710-CZ-MI-DCZM.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 0, 'es': 20, 'fr': 0, 'it': 1, 'pt': 6}` · 2º idioma: `pt` (6) · margen: 3.333x · chunks muestreados: 1

> **evidencia 1** (chunk_index 0): # Conexionado del módulo M710-CZ / MI-DCZM **Question** ¿Cómo conectar el módulo M710-CZ o MI-DCZM? **Answers El módulo M710-CZ no se puede instalar en zonas clasificadas con detectores de seguridad intrínseca.** La instalación de la zona convencional debe ser conforme a la normativa EN54-14: * No incluir dentro de la zona detectores y pulsadores * Nº máximo de pulsadores 10 * Nº máximo de detectores 32 Para conectar

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 15. `537a0275-920a-4e49-96ef-8d6d4570f06f` — propuesta: **en**

- stem: `156-0551-005R EPS10_Eng`
- fichero: `156-0551-005R EPS10_Eng` · marca: System Sensor
- marcadores por idioma: `{'en': 293, 'es': 0, 'fr': 0, 'it': 1, 'pt': 18}` · 2º idioma: `pt` (18) · margen: 16.278x · chunks muestreados: 8

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): INSTALLATION AND MAINTENANCE INSTRUCTIONS ! 3825 Ohio Avenue, St. Charles, Illinois 60174 1-800-SENSOR2, FAX: 630-377-6495 www.systemsensor.com # EPS10 Series Alarm Pressure Switches ## Specifications | Contact Ratings: | 10 A, 1/2 HP @ 125/250 VAC<br/>2.5A @ 6/12/24 VDC | | ---------------------------- | ---------------------------------------------------------------- | | Overall Dimensions: | See Figure 1 | | Opera

> **evidencia 2** (chunk_index 4, 2 anotacion(es) del extractor eliminadas): ## Figure 3. Switch terminals: - SWITCH #1 (top switch assembly) - COMMON TERMINALS - TERMINAL "A" - SWITCH #2 (second switch assembly) - TERMINAL "B" - GROUND SCREW (bottom left) - LOCKING SCREW (bottom center) BREAK WIRE AS SHOWN FOR SUPERVISION OF CONNECTION. DO NOT ALLOW STRIPPED WIRE LEADS TO EXTEND BEYOND SWITCH HOUSING. DO NOT LOOP WIRES. W0173-00 D770-08-00 3 156-0551-005R

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 16. `6096bdf6-27b6-41bb-a03a-e65bf90b5ea9` — propuesta: **es**

- stem: `MIE-MU-530rv001`
- fichero: `MIE-MU-530rv001` · marca: Morley
- marcadores por idioma: `{'en': 26, 'es': 188, 'fr': 9, 'it': 18, 'pt': 33}` · 2º idioma: `pt` (33) · margen: 5.697x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): # MORLEY IAS FIRE SYSTEMS # by Honeywell # ZX2e # ZX5e Documento No. MIE-MU-530rev.001 # Manual de Funcionamiento MORLEY-IAS PANELES DE INCENDIO ZX2e/ZX5e # Índice **1 INTRODUCCIÓN......................................................................................................................... 4** 1.1 AVISO ........................................................................................................

> **evidencia 2** (chunk_index 5, 1 anotacion(es) del extractor eliminadas): # 2 Niveles de acceso de usuario ## 2.1 Definición de nivel * Las centrales de alarma de incendio ZX1E, ZX2E y ZX5E disponen de tres niveles de acceso para el usuario. * En los tres niveles, los LEDS indican la condición de la instalación. Los LEDs de zona indican la ubicación de cualquier alarma de incendio o avería y la pantalla alfanumérica ofrece información más detallada sobre la alarma o avería. * En el NIVEL D

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 17. `09194202-db14-4299-867f-143d02267601` — propuesta: **en**

- stem: `3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet`
- fichero: `3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet.pdf` · marca: Kidde
- marcadores por idioma: `{'en': 205, 'es': 1, 'fr': 0, 'it': 0, 'pt': 2}` · 2º idioma: `pt` (2) · margen: 102.5x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 4 anotacion(es) del extractor eliminadas): # KIDDE **COMMERCIAL** # Excellence Series Intelligent Addressable Indoor Notification Device Installation Sheet EN DE ES FR IT NL PL PT **1** **2** **3** **4** ## EN: Installation Sheet ### Figures **Figure 1: VAD/VID lens and status LED** (1) VAD/VID lens (2) Status LED **Figure 2: Mounting base orientation for wall mounting** **Figure 3: Battery compartment and DIP switch** (1) DIP switch (2) Battery compartment (

> **evidencia 2** (chunk_index 5, 4 anotacion(es) del extractor eliminadas): ## Device status The device status is indicated by the status LED, as shown in the table below. | State | Indication | | ------------------- | ------------------- | | Isolation active | Steady yellow LED | | Device fault | Flashing yellow LED | | Located device \ | Steady green LED | | Communicating \ | Flashing green LED | Indicates an active Locate Device command from the control panel. This indication can be disab

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 18. `bc0c7b5f-95f7-4198-806c-b17dac41d32e` — propuesta: **es**

- stem: `TIDT110`
- fichero: `TIDT110.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 17, 'es': 63, 'fr': 0, 'it': 3, 'pt': 3}` · 2º idioma: `en` (17) · margen: 3.706x · chunks muestreados: 6

> **evidencia 1** (chunk_index 0): Honeywell **Información técnica** **TI-DT-110** **22/03/2010** # **NOTIFIER®** # **Convertidor RS232 a RS485/422 para TG a centrales ID3000 - punto a punto. Ref.: CONV232/485** Las conexiones de puerto serie RS-232 no están aconsejadas para longitudes de cableado superiores a 15/20 metros. Cuando existan caídas de tensión debidas a las longitudes del cable, es posible instalar convertidores de RS-232 a RS-485/422 en 

> **evidencia 2** (chunk_index 3): ## 2. Conexionado de la placa RS-232 del panel ID50/60 al convertidor Extremo A | Cable de placa RS-232 a Convertidor Extremo A | Cable de placa RS-232 a Convertidor Extremo A | | --------------------------------------------- | --------------------------------------------- | | Placa RS-232 en ID3000 | D-Sub-9/M Convertidor | | Rx PIN 3 | 2 (Tx) | | Tx PIN 2 | 3 (Rx) | | GND PIN 5 | 5 (GND) | **Selección de Interrupto

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 19. `f5224079-3c15-421a-83fe-5506edbc3100` — propuesta: **en**

- stem: `04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0`
- fichero: `04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0.pdf` · marca: Aritech
- marcadores por idioma: `{'en': 313, 'es': 4, 'fr': 1, 'it': 0, 'pt': 8}` · 2º idioma: `pt` (8) · margen: 39.125x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 11 anotacion(es) del extractor eliminadas): # Aritech APIC Installation Sheet for ModuLaser Aspirating Smoke Detection Systems **1** **2** | SW1 | SW2 | SW3 | | ------------------------------------ | ------------------------------------ | ------------------------------------ | | \ | \ | \ | | x100 | x10 | x1 | | Lowest Address | | | | SW4 | SW5 | SW6 | | ------------------------------------ | ------------------------------------ | -----------------------------

> **evidencia 2** (chunk_index 5): ## Interface details Analogue values for device status are shown in the table below. | Value | Status | | ----- | --------------------------------------------------- | | 1 | General Fault | | 2 | Flow/Filter Fault | | 3 | Disabled | | 4 | Internal APIC Fault (Hardware) | | 5 | Internal APIC Fault (Data Corruption) | | 6 | Internal APIC Fault (Parallel Comms – Ribbon Cable) | | 7 | Internal APIC Fault (Watchdog) | | 8

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 20. `217117c0-5b56-4225-9734-e600e5c4d8c7` — propuesta: **es**

- stem: `MADT212`
- fichero: `MADT212` · marca: Notifier
- marcadores por idioma: `{'en': 0, 'es': 202, 'fr': 18, 'it': 21, 'pt': 32}` · 2º idioma: `pt` (32) · margen: 6.312x · chunks muestreados: 6

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): **NOTIFIER ESPAÑA, S.A.** **Avda Conflent 84, nave 23** **Pol. Ind. Pomar de Dalt** **08916 Badalona (Barcelona)** **Tel.: 93 497 39 60; Fax: 93 465 86 35** # SUPLEMENTO DEL MANUAL DE INSTALACIÓN DE LA CENTRAL DE ALARMA CONTRA INCENDIOS SERIE ID1000

> **evidencia 2** (chunk_index 3): MA-DT-212 NOTIFIER ESPAÑA, S.A. 2 de 3 # Instalar/Reemplazar la tarjeta de lazo TX, Ref. 124-065 Para instalar la Tarjeta de lazo TX en su panel de la Serie 1000 siga el procedimiento de la Fase 1 descrito a continuación y en la Fase 2 en la página 3. Para reemplazar la tarjeta de lazo TX realice el procedimiento inverso descrito en la página 3. | **Fase 1 - Instalación de la placa** | Tome las precauciones adecuadas

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 21. `fc3d273e-7f99-402a-99e4-9099d8cefe8e` — propuesta: **en**  ⚠️ **PISTA MULTI-IDIOMA en el nombre: `['gb', 'it', 'ru']`**

- stem: `085501945t_PA5_Installation_manual_D-GB-F-RU-IT`
- fichero: `085501945t_PA5_Installation_manual_D-GB-F-RU-IT` · marca: Pfannenberg
- marcadores por idioma: `{'en': 380, 'es': 0, 'fr': 2, 'it': 0, 'pt': 5}` · 2º idioma: `pt` (5) · margen: 76.0x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 23 anotacion(es) del extractor eliminadas): 085 501 945t 30304-004t 1 # PA 5 / PA X 5-05/ PA X 5-10 - Betriebs- und Montageanleitung ## Maße **PA 5** Technical drawing showing three views: - Front view: Square housing 163.4 wide × Ø73 high, with circular speaker grille in center, four mounting holes at corners. Dimensions: 37 from edge, 143 between mounting holes - Side view: Depth 132 , showing M20-Ausbruch vorbereitet (M20 knockout prepared), 135 height - Bo

> **evidencia 2** (chunk_index 6, 3 anotacion(es) del extractor eliminadas): PATROL sounders and combined units **PA 5/ PA X 5** comply with the limits for a Class B digital device, pursuant to part 15 of the FCC Rules. ## UL/ cUL specifications: Suitable for indoor and outdoor use. Signaling area: see document 30304-005-1. <ins>Cable gland entries:</ins> Conduit installation needs to be UL/ cUL listed fittings suitable for knockout openings. The supply wiring has to be enclosed in metal cond

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 22. `0ad0a70f-f97b-4f88-90ff-65fad585ce51` — propuesta: **es**

- stem: `MA-AL-T500-01-07 Manual TUL500esp rev1`
- fichero: `MA-AL-T500-01-07 Manual TUL500esp rev1` · marca: Venitem
- marcadores por idioma: `{'en': 19, 'es': 195, 'fr': 12, 'it': 35, 'pt': 31}` · 2º idioma: `it` (35) · margen: 5.571x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): VENITEM # FUENTE DE ALIMENTACIÓN TUL500EN **CERTIFICADA con las normas EN 54-4:1997+A1:2002+A2:2006 EN 12101-10:2005** ## Manual de instalación ## CARACTERISTICAS GENERALES La Fuente de alimentación TUL500EN ha sido diseñada para ser utilizada como como una unidad de alimentación con Fuente de reserve para sistemas de detección y alarma de incendios, en conformidad con la regulación (EU) No 305/2011 y como equipo de 

> **evidencia 2** (chunk_index 5): ## Tipos y secciones recomendados de cables de instalación (certified EN50200) | Alimentación principañ 230 V\~ L-N-PE | FTG10OM1 0,6/1 kV: 3 x 1,5 mm²÷2,0 mm² | | ------------------------------------- | -------------------------------------- | | Terminales de salida A, B, C | FRHRRNS 2150: 2 x 1,5 mm²÷2,0 mm² | | Indicación entradas/Salidas | FRHRRNS 2050: 2 x 0,5 mm²÷1,5 mm² | Tab 4 **La fuente de alimentación ha s

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 23. `c295d7f9-f137-4ce4-96a6-d3fda323ba5c` — propuesta: **en**

- stem: `MNDT960I`
- fichero: `MNDT960I.pdf` · marca: Notifier
- marcadores por idioma: `{'en': 273, 'es': 0, 'fr': 0, 'it': 0, 'pt': 5}` · 2º idioma: `pt` (5) · margen: 54.6x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): NOTIFIER® FIRE SYSTEMS NOTIFIER ESPAÑA, S.A. Central: Avda. Conflent 84, Nave 23 Pol. Ind. Pomar de Dalt 08916 BADALONA (BARCELONA) Tel.: 93 497 39 60 Fax: 93 465 86 35 # POLLING BOARD # *POL-1* PRELIMINARY COPY # User Manual **MN-DT-9601 13 OCTOBER 2000** *All specifications are subject to change without notice* # POL-1 Instructions Manual ## <ins>Configuration Screen</ins> | \*\*Serial Port Configuration\*\* | | | 

> **evidencia 2** (chunk_index 5): ## Selecting devices Up to 20 devices can be monitored in the selected sequence by clicking on the check button ``` ┌────────────────────────────────────────┐ │ 02 ☑ │ └────────────────────────────────────────┘ ``` ``` ┌──┬───┬───┬───┬───┬──┬──┬──┬──┬───┐ │1 │26 │27 │29 │31 │2 │3 │4 │1 │42 │ ├──┼───┼───┼───┼───┼───┼──┼──┼───┼───┤ │41│50 │8 │105│106│107│2 │1 │16 │108│ └──┴───┴───┴───┴───┴───┴──┴──┴───┴───┘ 2 sec. ┌──┬

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 24. `4112c5c1-0362-407e-8713-bbd4e3fcbf9a` — propuesta: **es**

- stem: `MIE-MA-300_01`
- fichero: `MIE-MA-300_01.pdf` · marca: Morley
- marcadores por idioma: `{'en': 2, 'es': 317, 'fr': 27, 'it': 41, 'pt': 70}` · 2º idioma: `pt` (70) · margen: 4.529x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): MORLEY IAS FIRE SYSTEMS Morley-IAS Av.Industria,32 Bis. Posterior local 1 - Nave 2 P.I. Alcobendas 28108 - Madrid # <ins>ANEXO I</ins> al Manual MIE-MI-300 de la central analógica contra incendios ZX50 para la versión 5.02 con control de extinciones e integración. ## NOTAS IMPORTANTES ∑ Cualquier operación de carga y descarga con la versión de software **5.02** de la central ZX50 debe realizarse solo con la versión d

> **evidencia 2** (chunk_index 5): **EXS**. Relé de lazo de Extinción. Salida supervisada. Tipo de ID para módulos de control MI-CME para **sistema de extinción**. No se activa con las pruebas del sistema y permite ser anulado al anular los sistemas de extinción. Controla la línea de (En este caso solo se conectará la salida del módulo la resistencia final de línea de 47KW para la supervisión de la línea). MIE-MA-300_01A; 24/05/04 Morley-IAS ESPAÑA 5 

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 25. `3138edc4-6974-4a66-9357-02a10c60c46d` — propuesta: **en**

- stem: `I56-2956-000_prelim`
- fichero: `I56-2956-000_prelim.pdf` · marca: Morley
- marcadores por idioma: `{'en': 435, 'es': 53, 'fr': 7, 'it': 19, 'pt': 10}` · 2º idioma: `es` (53) · margen: 8.208x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): INSTALLATION AND MAINTENANCE INSTRUCTIONS MORLEY IAS FIRE SYSTEMS by Honeywell I56-2956-000 # MI-SC6 # Six Supervised Control Module Morley IAS Fire Systems Charles Avenue Burgess Hill, West Sussex, RH15 9UF ## SPECIFICATIONS Normal Operating Voltage: 15-32VDC Stand-By Current: 2.25 mA Alarm Current: 35 mA (assumes all six relays have been switched once and all six LEDs solid on) Temperature Range: -10°C to 55°C Humi

> **evidencia 2** (chunk_index 5): | **Circuit Components (Left Side):** | | | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | | 47K Resistor | Connected between terminals | | EOL Relay Connections | RED (–), BLK (–), with 47K resistor<br/>(+), (+) connections to VIO | | External 

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 26. `0dde8e85-4d91-4916-8c27-d3981fc564ca` — propuesta: **es**

- stem: `MIE-MC-130rv02`
- fichero: `MIE-MC-130rv02.pdf` · marca: Morley
- marcadores por idioma: `{'en': 6, 'es': 292, 'fr': 32, 'it': 38, 'pt': 31}` · 2º idioma: `it` (38) · margen: 7.684x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): MORLEY IAS FIRE SYSTEMS by Honeywell MK-VSN Documento No.MIE-MC-130rv002 Manual de Funcionamiento MORLEY-IAS MK-VSN Serie VISION Plus # Índice **1 INTRODUCCIÓN......................................................................................................................... 3** 1.1 AVISO .............................................................................................................................

> **evidencia 2** (chunk_index 5, 5 anotacion(es) del extractor eliminadas): # 4 Iniciar el Programa MK-VSN Una vez instalado el programa en su disco duro. Acceda a la carpeta donde haya copiado los archivos del programa y haga doble clic sobre el archivo **VSN.exe** o sobre el acceso directo del escritorio, si lo ha creado, para iniciar el programa de configuración MK-VSN. El programa solicita la **clave** de acceso, el **puerto de su serie de su PC** y el **Tipo de Conexión** con la central

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 27. `be1b6b42-721f-442f-a453-477a5e4dc795` — propuesta: **en**

- stem: `MNDT960I_iBox-BACnet`
- fichero: `MNDT960I_iBox-BACnet` · marca: Notifier
- marcadores por idioma: `{'en': 179, 'es': 2, 'fr': 0, 'it': 3, 'pt': 7}` · 2º idioma: `pt` (7) · margen: 25.571x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): **Honeywell Life Safety Iberia** C/Pau Vila 15-19 08911 Badalona (Barcelona) Tel.: 902 03 05 45 www.honeywelllifesafety.es www.notifier.es | infonlsiberia@honeywell.com # iBox BACnet/IP Gateway for the integration of Notifier ID3000 and Morley DXc fire panel series in BACnet/IP enabled monitoring and control systems. *User Manual* **MN-DT-960I 27 FEBRUARY 2013** (IBOX-BAC-NID3000 / r1 eng) *Information in this docume

> **evidencia 2** (chunk_index 5): | Element | Object supported | | -------- | ---------------------- | | Detector | • Status<br/>• Command | | Module | • Level | | Zone | • Status<br/>• Command | ## 1.3 *Capacity of iBox* iBox is capable of integrating one single Notifier ID3000 panel and its associated elements. | Element | Max. | Notes | | ----------------- | ---- | -----------------------------------------------------------------------------------

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 28. `d1299a40-5128-464d-b8d7-1c8c2b86562c` — propuesta: **es**

- stem: `DXc_Manual de configuracion`
- fichero: `DXc_Manual de configuracion` · marca: Morley
- marcadores por idioma: `{'en': 1, 'es': 245, 'fr': 15, 'it': 31, 'pt': 33}` · 2º idioma: `pt` (33) · margen: 7.424x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0): Honeywell | Fire Safety DX CONNEXION™ # Manual de configuración - PÁGINA 2 - # DX CONNEXION™ Manual de configuración # Índice | Sección | Título | Página | | --------- | ------------------------------------------------------ | ------ | | 1 | Introducción | 4 | | 1.1 | Avisos | 4 | | 1.2 | Modelos | 1 | | 1.3 | Advertencias y precauciones | 5 | | 1.4 | Requisitos nacionales | 6 | | 1.5 | Información EN54 | 4 | | 2 | D

> **evidencia 2** (chunk_index 5, 1 anotacion(es) del extractor eliminadas): ## 1.4 Requisitos nacionales * Este equipo debe instalarse siguiendo estas instrucciones y la normativa nacional y local aplicable. Consulte a la autoridad competente para confirmar dichos requerimientos. ---- **Todo el equipamiento debe instalarse de acuerdo a los requisitos nacionales y locales del lugar donde va a ser instalado.** ---- ## 1.5 Información EN54 Esta central de alarma contra incendios cumple los requ

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 29. `2c299ef1-4304-4253-9438-f37ab44a795e` — propuesta: **en**

- stem: `D 1148-1 BRS Notifier`
- fichero: `D 1148-1 BRS Notifier` · marca: Notifier
- marcadores por idioma: `{'en': 78, 'es': 25, 'fr': 21, 'it': 21, 'pt': 9}` · 2º idioma: `es` (25) · margen: 3.12x · chunks muestreados: 8

> **evidencia 1** (chunk_index 0): Estos dispositivos solo deben conectarse a paneles de control que utilicen un protocolo de comunicación direccionable analógico compatible y propio. La sirena base con detector integrado admite un detector avanzado de la serie 200. (Consulte las instrucciones del panel para confirmar la compatibilidad). Nota: Si el equipo de control no es capaz de tomar más de 99 direcciones de módulo, se generará un fallo por cada d

> **evidencia 2** (chunk_index 4): # Table 1 - VERSION 1 | DIP settingParamètre DIPDIP-SchaltereinstellungImpostazione DIPConfiguración DIPSW 1,2,3,4,5O=Off/1=On | No | PatternTypeMusterSchemaPatrón | Nominal FrequencyFréquence nominaleNennfrequenzFrequenza nominaleFrecuencia nominal | Max consumption (mA, RMS)Consommation max. (mA, RMS)Maximalverbrauch (mA, RMS)Consumo medio (mA, RMS)Consumo máximo (mA, RMS)Volume \| Volume | Max consumption (mA, RMS

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

## 30. `a107427f-5534-406b-b153-98c6e08e4524` — propuesta: **es**

- stem: `Manual Testifire_Spanish`
- fichero: `Manual Testifire_Spanish` · marca: Xtralis
- marcadores por idioma: `{'en': 2, 'es': 324, 'fr': 30, 'it': 27, 'pt': 71}` · 2º idioma: `pt` (71) · margen: 4.563x · chunks muestreados: 10

> **evidencia 1** (chunk_index 0, 1 anotacion(es) del extractor eliminadas): # testifire® COMPROBADOR DE DETECTOR MULTIESTÍMULO # Manual del usuario detectortesters testing technology from No Climb www.testifire.com

> **evidencia 2** (chunk_index 5): # Índice | | | N.° de página | | ------ | ------------------------------------------------------------------------------- | ------------- | | **1.** | **Instrucciones generales** | 4 | | | 1.1 Garantía | 4 | | | 1.2 Reconocimiento | 4 | | | 1.3 Reciclado | 4 | | **2.** | **Introducción** | 5 | | **3.** | **Identificación de piezas** | 6 | | **4.** | **Funcionamiento básico del equipo** | 7 | | | 4.1 Recargar las Bate

- [ ] OK  - [ ] MAL  → si MAL, idioma correcto: ______

---

**Recuento final:** ____ / 30 correctos. 30/30 -> gate (e)(iii) verde. Cualquier fallo -> HALT.
