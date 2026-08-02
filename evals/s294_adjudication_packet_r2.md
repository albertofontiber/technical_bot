# s294 — ADJUDICACIÓN CIEGA de capturas del gatillo «siempre» (L3 v2)

Eres el ADJUDICADOR. Cada fila es una oración extraída VERBATIM de un manual técnico de PCI del corpus. El sistema plantea usarlas como **avisos obligatorios** que se anexarían, citados y verbatim, al final de una respuesta técnica cuando el fragmento que las contiene se haya servido y la respuesta no las cubra.

**Tu tarea, fila por fila:** decidir si la oración es una **OBLIGACIÓN OPERATIVA REAL** que un técnico debe cumplir (`legitima`), o es **ESPURIA**. No sabes cuál es la fila que motivó el diseño, ni qué forma sintáctica capturó cada una: es deliberado.

## Taxonomía de ESPURIO (pre-registrada, fijada antes de mirar filas)

- **`condicional`** — «siempre y cuando» / «siempre que» — no es obligación, es condición
- **`descriptivo`** — describe conducta del equipo, no instruye al técnico («el LED permanece siempre fijo», «siempre recibe alimentación»)
- **`nota_de_diseno`** — comentario editorial/de diseño del manual, no obligación operativa
- **`fuera_de_dominio`** — obligación de otro circuito/producto que la pregunta no cubre (clase F8 del dúo: topología confundible = SEGURIDAD)
- **`span_roto`** — la cita verbatim no es utilizable: decapitada, fusionada o fragmento
- **`duplicado`** — la misma obligación ya emitida por otro átomo del mismo fragmento

**Regla de daño declarada:** cualquier fila adjudicada ESPURIA ⇒ STOP del lever

## Formato de respuesta (una línea por fila, sin prosa adicional)

`<n> | legitima|espuria | <clase de la taxonomía o '-'> | <≤12 palabras de motivo>`

Si una fila te parece dudosa, márcala `espuria` con la clase más cercana: el coste de un aviso de seguridad espurio es mayor que el de perder uno.

---

## Filas (60)

**1.** «Considere siempre lo importante que es el posicionamiento correcto de detectores de gas para obtener la respuesta óptima.»  
   <sub>fuente: MANUAL DETECTOR DE GAS VGN _SP rev 0 · p.4</sub>

**2.** «Tenga siempre en cuenta todos los avisos y precauciones del equipo.»  
   <sub>fuente: ATxxxS0x-MU - Manual Usuario AT Series rev1_0 · p.1</sub>

**3.** «* Utilice siempre los diodos de protección en los circuitos de carga conectados a la central si éstos son de tipo inductivo.»  
   <sub>fuente: MNDT503 · p.29</sub>

**4.** «• Utilice siempre los diodos de protección en los circuitos de carga conectados a la central si éstos son de tipo inductivo.»  
   <sub>fuente: MNDT506 · p.27</sub>

**5.** «Always test the device after installation to ensure that it communicates with the control panel.»  
   <sub>fuente: 3103072-ml_r004_excellence_series_intelligent_addressable_indoor_notification_device_installation_sheet · p.4</sub>

**6.** «Tenga siempre en cuenta todos los avisos y precauciones del equipo.»  
   <sub>fuente: MPS8ZS02 - MU-MANUAL DE USUARIO SERIE MPS rev2 · p.4</sub>

**7.** «* Always use the NeXT System Builder application to calculate the maximum number of APICs that can be installed.»  
   <sub>fuente: 04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0 · p.1</sub>

**8.** «Utilice siempre el software de cálculo de bucles System Builder para validar la carga de bucles prevista antes de la instalación.»  
   <sub>fuente: 10-5106-501-55nc-05_r005_iu2055nc_installation_sheet_ml · p.7</sub>

**9.** «Always refer to the Installation and Maintenance Instruction for specific recommendations on individual devices before installing the unit.»  
   <sub>fuente: I56-0986-004R EPS40_Eng · p.3</sub>

**10.** «> Asegúrese siempre de que las salidas y las alarmas que funcionan con el relé se inhiban o se aíslen antes de llevar a cabo cualquier trabajo en los sistemas de alarma.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.25</sub>

**11.** «Asegúrese siempre de descargar la corriente estática de su cuerpo antes de manejar paneles de circuitos.»  
   <sub>fuente: MNDT350 · p.2</sub>

**12.** «Asegúrese siempre de descargar la corriente estática de su cuerpo antes de manejar paneles de circuitos.»  
   <sub>fuente: MNDT120 · p.1</sub>

**13.** «Siga siempre un análisis estructurado de fallos y sistema de comprobación.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.27</sub>

**14.** «Utilice siempre las baterías de sustitución recomendadas.»  
   <sub>fuente: bcn-3100017-es_r002_nc_series_fire_alarm_control_panel_installation_manual · p.95</sub>

**15.** «> Asegúrese siempre de que los sistemas de alarma vuelvan al estado de Funcionamiento normal cuando haya finalizado el trabajo.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.26</sub>

**16.** «Always test the device after installation to ensure that it communicates with the control panel.»  
   <sub>fuente: 3103198-ml_r002_excellence_series_intelligent_addressable_outdoor_notification_device_installation_sheet · p.4</sub>

**17.** «> Asegúrese siempre de que las salidas y las alarmas que funcionan con el relé se inhiban o se aíslen antes de llevar a cabo cualquier trabajo en los sistemas de alarma.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.27</sub>

**18.** «Always disconnect the exterior bipolar magnetothermic switch before working in the panel.»  
   <sub>fuente: CCD-103_Manual_ES_FR_GB_IT · p.54</sub>

**19.** «Always test detectors after installation to ensure that the detector communicates with the control panel.»  
   <sub>fuente: 3102986-ml_r002_excellence_series_intelligent_addressable_class_a-b_heat_detector_installation_sheet · p.2</sub>

**20.** «> Asegúrese siempre de que las salidas y las alarmas que funcionan con el relé se inhiban o se aíslen antes de llevar a cabo cualquier trabajo en los sistemas de alarma.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.26</sub>

**21.** «Coloque siempre las baterías con los terminales hacia el exterior (véase la ilustración de la izquierda) para evitar que alguna parte del potenciador de lazo pueda causar un cortocircuito.»  
   <sub>fuente: MIDT1500_A · p.7</sub>

**22.** «Revise siempre la hoja de instalación del aislador o dispositivo para conocer con exactitud los requisitos y las limitaciones.»  
   <sub>fuente: 00-3280-501-4009-05_r005_2x-a_series_installation_manual_es · p.42</sub>

**23.** «Desconecte siempre el magnetotérmico bipolar exterior antes de manipular la central.»  
   <sub>fuente: CCD-103_Manual_ES_FR_GB_IT · p.12</sub>

**24.** «Coloque siempre el detector a un mínimo de 0,5 m de cualquier protuberancia.»  
   <sub>fuente: Manual de usuario Issue 0165-02 v2 MI 546 es 2022 FIREBEAM BLUE · p.4</sub>

**25.** «Lleve siempre una muñequera antiestática adecuada antes de manipular los circuitos para descargar del cuerpo la electricidad estática.»  
   <sub>fuente: I56-3918-001 IM-10EA_multi · p.5</sub>

**26.** «Asegúrese siempre de descargar la corriente estática de su cuerpo antes de manejar paneles de circuitos.»  
   <sub>fuente: MPDT170 · p.1</sub>

**27.** «Confirme siempre la configuración de la puerta de enlace con su administrador de red.»  
   <sub>fuente: 3103092-es_r003_modulaser_en_54-20_installation_manual_kidde_0 · p.45</sub>

**28.** «Lleve siempre una muñequera antiestática adecuada antes de manipular los circuitos para descargar del cuerpo la electricidad estática.»  
   <sub>fuente: NFXI-RM6_DS_EN_I56-3977-001_2013_Multi · p.5</sub>

**29.** «Revise siempre las características técnicas de consumos de cada equipo conectado al lazo analógico, publicadas por el fabricante.»  
   <sub>fuente: MIE-MI-530rv001 · p.38</sub>

**30.** «> Asegúrese siempre de que los sistemas de alarma vuelvan al estado de Funcionamiento normal cuando haya finalizado el trabajo.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.27</sub>

**31.** «Always ensure that the mains cables are brought into the back box separately to the low-voltage wiring.»  
   <sub>fuente: HLSI-MI-130I · p.15</sub>

**32.** «Always ensure that the mains cables are brought into the back box separately to the low-voltage wiring.»  
   <sub>fuente: MN-DT-102I · p.9</sub>

**33.** «Lleve siempre una muñequera antiestática adecuada antes de manipular los circuitos para descargar del cuerpo la electricidad estática.»  
   <sub>fuente: I56-3976-001 NFXI-MM10 · p.5</sub>

**34.** «* Utilice siempre los diodos de protección en los circuitos de carga conectados a la central si éstos son de tipo inductivo.»  
   <sub>fuente: MNDT500 · p.27</sub>

**35.** «Always ensure that the mains cables are brought into the back box separately to the low-voltage wiring.»  
   <sub>fuente: MIEMN570I · p.9</sub>

**36.** «Considere siempre lo importante que es el posicionamiento correcto de detectores de gas para obtener la respuesta óptima.»  
   <sub>fuente: VGS EXPLOSIVOS _SP rev 1 · p.7</sub>

**37.** «Tenga siempre mucho cuidado al utilizar las opciones del menú «Administración de Configuración».»  
   <sub>fuente: 997-671-005-3_Configuration_ES · p.57</sub>

**38.** «Always use the NeXT System Builder application to calculate the maximum number of modules that can be installed.»  
   <sub>fuente: 3103062-ml_r003_excellence_series_addressable_single_output_module_installation_sheet · p.1</sub>

**39.** «Confirme siempre la configuración de la puerta de enlace con su administrador de red.»  
   <sub>fuente: 04-4001-501-2009-12_r012_modulaser_en_54-20_installation_manual_es_edwards_0 · p.44</sub>

**40.** «Always disconnect the control panel from the mains supply before changing the power setting.»  
   <sub>fuente: 00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0 · p.46</sub>

**41.** «Siga siempre todas las advertencias e indicacione que el equipo pueda darle.»  
   <sub>fuente: LDA VCC-64 - Manual de Usuario · p.4</sub>

**42.** «Considere siempre lo importante que es el posicionamiento correcto de detectores de gas para obtener la respuesta óptima.»  
   <sub>fuente: VGS TOXICOS _SP rev 1 · p.7</sub>

**43.** «Tome SIEMPRE nota de este valor como parte de su mantenimiento de rutina para ver cualquier patrón de acumulación.»  
   <sub>fuente: Manual DBD_70A (55310016 MI 471 m 2021 d) · p.17</sub>

**44.** «Always use the NeXT System Builder application to calculate the maximum number of APICs that can be installed with or without the adaptor board.»  
   <sub>fuente: 04-4001-501-1700-06_r006_aritech_apic_installation_sheet_ml_0 · p.2</sub>

**45.** «Consulte siempre la legislación y normativa aplicable, por ejemplo: UNE 23007-14, etc...»  
   <sub>fuente: 55356500-Manual-Sirena-Analogica-MAD565-I_ES_GB_MI-466-m-2020-e · p.1</sub>

**46.** «Desconecte siempre el magnetotérmico bipolar exterior antes de manipular la central.»  
   <sub>fuente: 55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT · p.12</sub>

**47.** «Utilice siempre la aplicación NeXT System Builder para calcular el número máximo de módulos que se pueden instalar.»  
   <sub>fuente: 3103063-ml_r003_excellence_series_addressable_two-four_input-output_module_installation_sheet · p.10</sub>

**48.** «* Always replace all batteries at the same time and use batteries of the same type.»  
   <sub>fuente: HLSI-MN-103I_RP1r-Supra_lr · p.71</sub>

**49.** «Cumpla siempre con los requisitos de los códigos y normas aplicables, como NFPA 72, National Fire Alarm Code, BS 5839-1 NFS 61.970, R7, AS1670.1 y GB50166, etc., así como las directivas de la autoridad con jurisdicción.»  
   <sub>fuente: E56-6514ES-000_Notifier_NFXI-OSI-RIE_Installation_Guide · p.8</sub>

**50.** «Always disconnect the exterior bipolar magnetothermic switch before working in the panel.»  
   <sub>fuente: 55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT · p.46</sub>

**51.** «Desconecte siempre el suministro eléctrico a la central antes de instalar una tarjeta de expansión.»  
   <sub>fuente: bcn-3100017-es_r002_nc_series_fire_alarm_control_panel_installation_manual · p.30</sub>

**52.** «> Asegúrese siempre de que los sistemas que funcionan con relé (rociadores, alarmas, etc.) estén inhibidos o desactivados antes de utilizar esta lámpara de comprobación cerca de cualquier detector de llamas.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.35</sub>

**53.** «Always disconnect the mains power before handling the panel.»  
   <sub>fuente: 55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT · p.20</sub>

**54.** «Utilice siempre un cable de calibre adecuado.»  
   <sub>fuente: A05-7030-100_B_ES_Morley FAAST FLEX Addressable · p.27</sub>

**55.** «Utilice siempre las baterías de sustitución recomendadas.»  
   <sub>fuente: 00-3280-501-4009-05_r005_2x-a_series_installation_manual_es · p.155</sub>

**56.** «> Asegúrese siempre de que los sistemas de alarma vuelvan al estado de Funcionamiento normal cuando haya finalizado el trabajo.»  
   <sub>fuente: 2055M1000_ES MAN0987_ISS 1_Rev 4 FSL100 Technical Handbook · p.30</sub>

**57.** «Preste siempre mucha atención y utilice siempre equipo protector adecuado cuando trabaje en altura con el fin de evitar el riesgo de sufrir lesiones personales.»  
   <sub>fuente: Manual Testifire_Spanish · p.5</sub>

**58.** «Revise siempre las características técnicas de consumos de cada equipo conectado al lazo analógico, publicadas por el fabricante, para cada tipo de equipo.»  
   <sub>fuente: MIE-MI-530rv001 · p.38</sub>

**59.** «Always refer to the Installation and Maintenance Instruction for specific recommendations on individual devices before installing the unit.»  
   <sub>fuente: 156-0551-005R EPS10_Eng · p.3</sub>

**60.** «Always disconnect the bi-polar breaker before working in the repeater.»  
   <sub>fuente: 55315501 CAD150R Instalacion ES GB 191018 · p.14</sub>
