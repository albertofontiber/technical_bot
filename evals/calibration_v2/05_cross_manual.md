# Calibración del judge v2 — categoría `cross_manual` (8 preguntas)

**Origen:** `logs/eval_20260502T152857Z.json` (eval del 2 mayo 2026).

**Categoría:** Pregunta menciona varios fabricantes -> política: NO inferir cross-brand.

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

## cm001 — judge dice **PASS ✓** · (1/8)

**Pregunta del técnico:** ¿Puedo usar un detector Notifier SDX-751 con una central Morley ZXe?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Cross-brand: política usuario confirmada 22-abril = NO inferir cross-brand aunque se advierta la fuente. Behavior correcto = admit_no_info + remitir a ambos fabricantes. Revisado en audit 22-abril (prev: answer)._

### Fragmentos que el bot usó (top 5)

**[F1]** `SDX-751EM` · *ADVERTENCIA Desconecte el suministro eléctrico de lazo antes de instalar los sensores.* · `I56-1306-002_SDX-751EM` p.3 · sim 0.65

```
ADVERTENCIA
Desconecte el suministro eléctrico de lazo antes de instalar los sensores.

ADVERTENCIA
Desconecte el suministro eléctrico de lazo antes de instalar los sensores.

4
4
0
2
3
1
0
ONES
TENS
2
3
1
6 7
5
5
9
8
6
9
8
7
INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO DEL SENSOR
DE HUMO ÓPTICO ANALÓGICO DIRECCIONABLE MODELO SDX-751EM
Antes de instalar el sensor, lea detenidamente el manual de conexión e instalación de System Sensor, I56-407-XX, Guía Para el Uso Adecuado
Detectores de Humo. Dicho manual contiene información detallada sobre la distancia, ubicación, tipo de zonas y aplicaciones especiales del
sensor. Pueden obtenerse copias de este manual sin cargo, previa solicitud a Notifier.
DESCRIPCIÓN GENERAL
Los sensores ópticos analógicos direccionables modelo SDX-751EM son detectores de conexión que combinan una cámara de detección
fotoelectrónica con comunicaciones analógicas direccionables. Se han diseñado dichos sensores para la protección de zonas diáfanas y sólo
deben conectarse a cuadros de control que empleen un protocolo propio de comunicacines que sea compatible y direccionable analógicamente
para la supervisión y el control.
En cada sensor se iluminan dos diodos fotoemisores (LED) indicando la detección desde cualquier punto visible. Se pueden enclavar mediante
una orden procedente de la central. También se pueden desenclavar a estado normal mediante una orden procedente de la central. Se puede
disponer de un LED indicador remoto como accesorio opcional conectado a los terminales de base estándar.
CARACTERÍSTICAS
Límites de Tensión de Funcionamiento
de 15 a 32 Vdc
Corriente en Estado de Reposo
230 µA @ 24 Vdc (sin comunicación)
Media Máxima de Corriente en Estado de Reposo
330 µA (comunicaciones cada 5 seg. con el LED intermitente activado)
Corriente Má
[… contenido truncado para legibilidad]
```

**[F2]** `SDX-751EM` · *Abb. 3   Drehschalter für Adressierung* · `I56-1306-002_SDX-751EM` p.4 · sim 0.65

```
Abb. 3   Drehschalter für Adressierung

Abb. 3   Drehschalter für Adressierung

INSTALLATIONS- UND WARTUNGSANLEITUNG FÜR DIE ADRESSIERBAREN
EXTREM FLACHEN OPTISCHEN RAUCHMELDER SDX-751EM
Allgemeine Beschreibung
Der analoge adressierbare Rauchmelder SDX-751EM verwendet eine optische Meßkammer nach dem Streulichtprinzip. Dieser Rauchmelder ist
nur für die dafür vorgesehenen Brandmelderzentrale einzusetzen. Er kann in eine Vielzahl von unterschiedlichen Montage-Sockeln eingebaut
werden.
Zwei LEDs an jedem Melder ermöglichen eine 360°-Anzeige am Melder, die von der Brandmelderzentrale im Alarmfall oder zur Störungsanzeige
angesteuert werden. Für den Normalbetrieb können sie im Blink-Modus angesteuert werden. Der Anschluß eines Melderparallelindikators zur
abgesetzen Anzeige eines Alarms ist möglich.
Technische Daten
Betriebsspannung:
15V bis 32V DC
Max. Ruhestrom:
230µA @ 24V DC (ohne Datenaustausch)
Max. durchschn. Ruhestrom(arithm.)
330µA (1 Abfrage in 5s mit LED-Blinkmodus)
Max. Alarmstrom (LED an)
6,5mA @24V DC
Luftfeuchtigkeit:
10% bis 93% rel. Luftfeuchtigkeit (nicht kondensierend)
Umgebungstemperatur:
-30°C – +80°C
Höhe:
43mm installiert in Sockel B501
Durchmesser:
102mm installiert in Sockel B501
Gewicht:
115g
Dieser Rauchmelder wurde nach prEN54 Teil7 getestet und zertifiziert.
Installation
Die Einzelheiten zum Anschluß des Meldersockels sind der Anschlußanleitung der Meldersockel zu entnehmen, die den Sockeln beigefügt sind.
Anmerkung: Die Verdrahtung muß den lokalen Vorschriften und Anforderungen entsprechen.
Stellen Sie sicher, daß die Meldersockel korrekt verdrahtet sind und Kurzschlüsse oder vertauschte Adern auszuschließen sind.
Warnung
Bevor die Melder und Sockel installiert werden, sollte die Spannungsversorgung für die Brandmelderzentrale
 abgeschaltet wer
[… contenido truncado para legibilidad]
```

**[F3]** `SDX-751EM` · *WARNING Disconnect loop power before installing sensors.* · `I56-1306-002_SDX-751EM` p.1 · sim 0.65

```
WARNING
Disconnect loop power before installing sensors.

WARNING
Disconnect loop power before installing sensors.

SENSING
CHAMBER
SENSOR
SCREEN
SENSOR
COVER
COVER
REMOVAL TABS
4
4
0
2
3
1
0
ONES
TENS
2
3
1
6 7
5
5
9
8
6
9
8
7
TESTING
Sensors must be tested after installation and following periodic maintenance.  However,
before testing, notify the proper authorities that the smoke detector system is undergoing
maintenance and  the system will be temporarily be out of service. Disable the zone or
system undergoing maintenance to prevent unwanted alarms.
In addition, check to ensure that the LEDs blink (if this feature is operational under software
command).  If they do not, power has been lost to the sensor (check the wiring) if it is
defective (return it for repair).
Test the sensors as follows:
1.
Test the sensor by positioning the test magnet (Model M02-24-optional) against the sensor body approximately 2cm from LED1 in the
direction of the metering socket as shown in Figure 1.
2.
Both LEDs should latch on within 30 seconds indicating an alarm and activating the panel.
After completion of this test notify the proper authorities that the system is operational.
Sensors that fail this test shoud be cleaned as described under MAINTENANCE and retested.  If the sensors still fail this test they should be
returned for repair.
WARNING
LIMITATIONS OF SMOKE DETECTORS
This smoke detector is designed to activate and initiate emergency action, but will do so only when used in conjunction with other equipment.
Smoke detectors will not work without power.
Smoke detectors will not sense fires which start where smoke does not reach the detectors. Smoke from fires in chimneys, in walls, on
roofs, or on the other side of closed doors may not reach the smoke detector and trigger the uni
[… contenido truncado para legibilidad]
```

**[F4]** `ZXe` · *Carga y monitorización de Baterías en reposo* · `MIE-MP-530rv001` p.6 · sim 0.80

```
Carga y monitorización de Baterías en reposo

MORLEY-IAS 
 
Paneles de Incendio ZX2e/ZX5e 
 
Página 6 de 66 
Documento No. MIE-MP-530 revisión: 001  
Manual de Configuración 
1.3 Requerimientos Nacionales y Locales 
Este equipamiento debe instalarse de acuerdo con los requerimientos nacionales y locales propios del lugar donde va a 
colocarse. Consulte a la autoridad pertinente para confirmar dichos requerimientos. 
 
Todo equipamiento debe ser instalado de acuerdo a los requerimientos nacionales y 
locales propios del lugar donde va a ser instalado 
 
1.4 Información EN54 
 
EN54
!
 
EN54-2 13.7 
Máximo 512 
sensores / 
pulsadores por 
panel. 
• 
Los paneles ZX2e y ZX5e disponen de algunas funciones que en 
caso de usarse de forma inapropiada, pueden contravenir los 
requerimientos de la normativa EN54. En los casos en que pueda 
suceder, se mostrará una advertencia con datos de la norma EN54 y 
la sección pertinente de la misma. Se muestra una advertencia típica 
en este sentido. 
 
 
EN54
9
 
• 
Este panel de control contra incendios cumple con los requerimientos de EN54-2/4 
1997. Adicionalmente sobre los requerimientos básicos obligatorios de la norma 
EN54, el panel dispone de las siguientes opciones reguladas: 
 
Funciones opcionales 
Cláusula EN54-2  
 
Indicación: 
Averías de puntos 
Controles: 
Detección por coincidencia 
 
Retardos de activación de Salidas 
 
Anulación de cada punto direccionable 
 
Prueba 
Salidas: 
Salidas para equipos de incendio 
 
8.3 
7.12 
7.11 
9.5 
10 
7.8 
 
 
EN54
9
 
• 
La Fuente de alimentación de los paneles ZX2e y ZX5e cumplen con los siguientes 
requerimientos de la norma EN54-4: 
 
Funciones Fuente de Alimentación ZX2e & ZX5e 
Cláusula EN54-4 
 
Alimentación derivada de la Fuente principal 
Alimentación derivada de Baterías e
[… contenido truncado para legibilidad]
```

**[F5]** `ZXe` · *1.4 Información EN54* · `MIE-MP-530rv001` p.6 · sim 0.80

```
1.4 Información EN54

MORLEY-IAS 
 
Paneles de Incendio ZX2e/ZX5e 
 
Página 6 de 66 
Documento No. MIE-MP-530 revisión: 001  
Manual de Configuración 
1.3 Requerimientos Nacionales y Locales 
Este equipamiento debe instalarse de acuerdo con los requerimientos nacionales y locales propios del lugar donde va a 
colocarse. Consulte a la autoridad pertinente para confirmar dichos requerimientos. 
 
Todo equipamiento debe ser instalado de acuerdo a los requerimientos nacionales y 
locales propios del lugar donde va a ser instalado 
 
1.4 Información EN54 
 
EN54
!
 
EN54-2 13.7 
Máximo 512 
sensores / 
pulsadores por 
panel. 
• 
Los paneles ZX2e y ZX5e disponen de algunas funciones que en 
caso de usarse de forma inapropiada, pueden contravenir los 
requerimientos de la normativa EN54. En los casos en que pueda 
suceder, se mostrará una advertencia con datos de la norma EN54 y 
la sección pertinente de la misma. Se muestra una advertencia típica 
en este sentido. 
 
 
EN54
9
 
• 
Este panel de control contra incendios cumple con los requerimientos de EN54-2/4 
1997. Adicionalmente sobre los requerimientos básicos obligatorios de la norma 
EN54, el panel dispone de las siguientes opciones reguladas: 
 
Funciones opcionales 
Cláusula EN54-2  
 
Indicación: 
Averías de puntos 
Controles: 
Detección por coincidencia 
 
Retardos de activación de Salidas 
 
Anulación de cada punto direccionable 
 
Prueba 
Salidas: 
Salidas para equipos de incendio 
 
8.3 
7.12 
7.11 
9.5 
10 
7.8 
 
 
EN54
9
 
• 
La Fuente de alimentación de los paneles ZX2e y ZX5e cumplen con los siguientes 
requerimientos de la norma EN54-4: 
 
Funciones Fuente de Alimentación ZX2e & ZX5e 
Cláusula EN54-4 
 
Alimentación derivada de la Fuente principal 
Alimentación derivada de Baterías en reposo 
Carga y monito
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo documentación sobre interoperabilidad entre el detector **SDX-751EM** (Notifier) y la central **ZXe** (Morley-IAS) en mi base.

Lo que sí puedo confirmar a partir de los fragmentos disponibles es relevante para entender por qué esto no es trivial:

- El **SDX-751EM** utiliza un **protocolo de comunicaciones analógico direccionable propietario**, y su manual indica explícitamente que "sólo deben conectarse a cuadros de control que empleen un protocolo propio de comunicaciones que sea compatible y direccionable analógicamente" [F1].
- Los fragmentos del **ZXe** disponibles cubren únicamente configuración general y cumplimiento **EN54-2/4** [F4][F5], sin mencionar listas de dispositivos compatibles ni protocolos de lazo admitidos.

Dado que el SDX-751EM requiere compatibilidad de protocolo con la central [F1], y los fragmentos del ZXe no especifican qué detectores o protocolos admite, **no puedo confirmar ni descartar la compatibilidad** con los datos que tengo.

**Recomendación:** Consulta directamente a Morley-IAS y a Notifier para verificar la compatibilidad de protocolo entre ambos equipos.

---

Fuentes: I56-1306-002_SDX-751EM (sin revisión registrada); MIE-MP-530rv001 (revisión 001)
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no tiene información de compatibilidad entre el SDX-751EM y la ZXe, lo cual es la conducta esperada (admit_no_info). Las dos afirmaciones técnicas que hace están soportadas por los fragmentos citados: el requisito de protocolo propietario compatible del SDX-751EM aparece literalmente en F1/F3, y la cobertura limitada de los fragmentos ZXe a EN54-2/4 está en F4/F5. No inventa compatibilidad ni datos de protocolo del ZXe, y redirige al técnico a los fabricantes, lo

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

La respuesta correcta combinando manuales sería: NO compatibles. Hay que cruzar (a) manual SDX-751EM (I56-1306-002) que indica que el detector "sólo deben conectarse a cuadros de control que empleen un protocolo propio de comunicaciones que sea compatible y direccionable analógicamente" — protocolo propietario Notifier/CLIP; (b) manual ZXe (MIE-MP-530) que es Morley-IAS con su propio protocolo; y crucialmente (c) **el documento oficial Honeywell "Compatibilidad entre equipos Notifier y Morley" (Manuales_Morley_Guias/) que dice expresamente: "No, no es posible instalar equipos de Notifier en una central de Morley… los protocolos de comunicación son distintos y los equipos no comunicarán, además la central indicará AVERÍA DE TRANSMISIÓN"**. La info SÍ existe en el corpus si miramos a través de varios manuales.

**Calidad de los chunks:**

- F1-F3 son del manual SDX-751EM (Notifier/System Sensor); F4-F5 del ZXe (Morley). Vienen de manuales separados de distintos fabricantes (mismo grupo Honeywell pero protocolos distintos).
- F2 está en alemán — ruido de retrieval, debería filtrarse por idioma.
- F4 y F5 son casi duplicados (mismo p.6 del MIE-MP-530, solo difiere el header de chunk).
- Falta crítica: no se recupera el manual de Compatibilidad Honeywell que daría la respuesta cerrada.

**Comparación con bot:**

- El bot combinó info de F1+F4 correctamente (señala el problema de protocolo propietario), pero al no tener el chunk de la guía de compatibilidad Honeywell, no pudo cerrar la respuesta como "no, no compatible".
- Dijo "no puedo confirmar ni descartar" cuando con el chunk correcto la respuesta sería un "no" claro.

**Veredicto:**
- [x] **De acuerdo** con el judge (dada la política cross-brand vigente y los F que vio)
- **Dimensión equivocada(s) del judge:** ninguna sobre lo visible
- **Nota / por qué:** **Atención al recalibrado**: la recalibración answer→admit_no_info es defensible como política pero **enmascara un fallo de retrieval**: existe un manual oficial Honeywell que zanja la pregunta y no se recupera. El bot debería poder responder "no compatible" con esa fuente.
- **Origen del problema:** retrieval (falta indexar/priorizar la guía Honeywell de Compatibilidad)

---

## cm002 — judge dice **PASS ✓** · (2/8)

**Pregunta del técnico:** Necesito migrar de una Notifier AFP-200 antigua a una ID3000, manteniendo el cableado existente

**Conducta esperada:** `answer` · **observada:** `admit_no_info`

**Keyword score:** 4/4 hits · missing: `[]` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `AFP-200E` · *Nota: La resistencia máxima del circuito es de 20 ohms.* · `MNDT120` p.31 · sim 0.82

```
Nota: La resistencia
máxima del circuito es
de 20 ohms.

31
MN-DT-120
NOTIFIER ESPAÑA, S.A.
3
MMX-1
AFP-200
24V (+) TB1-5
24V (-)  TB 1-6
Detector
térmico
mecánico
Relé de supervisión
de la alimentación
Detector de
de 4 hilos
24 Vdc
Pulsador
 manual
Lazo de
salida
Hacia el siguiente
equipo del lazo
+          -
Alimentación
rearmable
SLC (+) TB 6-3
SLC (-)  TB 6-5
Figure 2-14: Bucle de activación Estilo D de la NFPA
Supervisado y de intensidad limitada
 A   B  B+ A+ B- A-
Nota: La resistencia
máxima del circuito es
de 20 ohms.


[TABLA EXTRAÍDA]
| Figure | 2-14: | Bucle de activac | ión Estilo D de la NF | PA |  | 
----------------------------------------
 |  |  | Supervisado y de inte | nsidad limitada |  |  | 
 |  |  |  | Relé de su | pervisió | n | 
 |  |  |  | de la alim | entació | n | 
 |  |  |  | Detector de |  |  | 
 |  |  |  | de 4 hilos |  |  | 
 |  |  |  | 24 Vdc |  |  | 
 |  |  |  | Pulsador |  |  | 
 |  |  |  | manual | Nota: | La r | esisten
 |  |  |  |  | máxim | a del | circuito
 |  |  |  |  | de 20 | ohms. | 
H | acia el sig | uiente |  |  |  |  | 
 | equipo del | lazo |  |  |  |  | 
 | + | - |  |  |  |  | 
limentación rearmable |  |  |  |  | Detector térmico mecánic | o | 
L | azo de |  |  |  |  |  | 
s | alida |  | MMX-1 3 |  |  |  | 
 |  |  |  |  | A | B B+ | A+ B- A-
24V (+) TB1-5 |  |  |  |  | S | LC (+) | TB 6-3
24V (-) TB 1-6 |  |  | AFP | -200 | S | LC (-) | TB 6-5
32
MN-DT-120
NOTIFIER ESPAÑA, S.A.
AFP-200
Detectores de
dos hilos
B + B - B + B - B + B - B + B -
N O C N O N C C N O N C C
+ - + - + -
A 
B 
A - 
B - 
A + 
B +
T
B
3
T
B
2
T
B
1
T
B
6
TX REF RX REF
OUT OUT IN IN
T
B
5
T
B
4
+    -
+    -
+    -
+    -
Alimentación
filtrada,
rearmable de
24 Vdc
ELR
de 3.9K
MMX-2
SLC (+) TB 6-3
SLC (-)  TB 6-5
24V (+) TB1-5
24V (-)  TB 1-6
Para más in
[… contenido truncado para legibilidad]
```

**[F2]** `ID3000` · *Valores de salida de contacto libre de tensión (VFC) Tipo: Conmutador unipolar Carga máxima: Contactos de 30V 1A Valor f* · `MIDT190` p.68 · sim 0.80

```
Valores de salida de contacto libre de tensión (VFC)
Tipo:
Conmutador unipolar
Carga máxima:
Contactos de 30V 1A
Valor fusible:
No aplicable (sin fusible)

Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 2
MI-DT-190_D
    A2-4
Salidas:
i)
Dos salidas de sirena
ii) Dos salidas seleccionables - Sirena o contacto libre de tensión
(VFC)
iii) Dos salidas de contacto libre de tensión dedicadas a alarma
común y fallo común.
iv) Dos salidas de lazo estándar, o bien, opcionalmente, hasta
ocho salidas de lazo.
v) Dos salidas auxiliares de 24Vdc.
Valores de salida de sirena
Tipo:
Tensión invertida
Tensión de salida:
de 26 a 28V cuando está activa;
de -6,8V a -9V cuando está inactiva
Carga máxima:
1A *
Fusible:
Protección sobrecorriente
electrónica
Supervisión:
Circuito abierto y cortocircuito
Valores de salida de contacto libre de tensión (VFC)
Tipo:
Conmutador unipolar
Carga máxima:
Contactos de 30V 1A
Valor fusible:
No aplicable (sin fusible)
Baterías:
Baterías internas:
Se DEBEN utilizar dos baterías de plomo
ácido selladas de 12V, 12-38Ah. Su vida
útil depende de la temperatura ambiente;
consulte las especificaciones del
fabricante de las baterías. (Véase las
especificaciones de la FA para las
limitaciones del cargador).
Valores máximos de las baterías:
Caja y opción tipo de batería:
Yuasa
Caja estándar:
12Ah
Caja ampliada o de doble ampliación:
17Ah
Caja con fondo ampliado/fondo
doble ampliación:
38Ah
Cabina para batería independiente:
130Ah
Baterías externas:
Consulte la documentación de la cabina
de las baterías para más detalles. Su vida
útil depende de la temperatura ambiente;
consulte las especificaciones del
fabricante de las baterías. (Véase las
especificaciones de la FA para las
limitaciones del cargador).
Nota: Con el kit de fuente de alimentación de
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *Introducción* · `MCDT191_1` p.25 · sim 0.82

```
Introducción

Introducción

Introducción
ID3000 - Manual del programa de configuración PK-ID3000
MC-DT-191_F v. 2.17e
     19
1.5.11 Menú de sistemas externos
Este menú dispone de opciones para
configurar Puntos virtuales que existen en un
sistema externo (por ejemplo un equipo de
alarma o evacuación por megafonía). Los
Puntos virtuales se comunican con la central
de alarmas de incendio a través de una
conexión RS232 (no a través de los lazos) y
se utilizan como entradas o salidas en la Matriz
de control. Hay dos tipos de puntos virtuales:
a. Puntos virtuales de entrada (VIP). Se puede
configurar un máximo de 64.
b. Puntos virtuales de salida (VOP). Se puede
configurar un máximo de 512.
Para configurar un VIP o un VOP:
i
En el menú de Sistemas Externos,
seleccione ‘Puntos virtuales de entrada’ o
‘Puntos virtuales de salida’.
ii
Otorgue un nombre al punto (con un máximo
de 32 caracteres).
iii Asigne un número de zona. Los VIP y los
VOP deben estar en una zona antes de
que la Matriz de control los pueda
reconocer. El número de VIP y VOP que
puede haber en una zona es ilimitado, sin
embargo, en modo VdS (solo en Alemania)
no se pueden poner en la misma zona como
sensores o pulsadores (DKM) y  no
disponen de número de referencia.
Nota: Las descripciones de las zonas no se
pueden modificar en esta pantalla.
Consulte la Sección 1.5.9.
iv VOP (punto virtual de salida): Seleccione
el tipo (SIR o CTRL) y el modo (Silenciable
o no silenciale). El VOP se incluirá en la
matriz de control utilizando el tipo
seleccionado.
VIP (punto virtual de entrada): Seleccione
el tipo (Alarma o Activación técnica /
Auxiliar). El VIP se visualizará en la pestaña
adecuada de la central.
VENTANA DE PUNTOS VIRTUALES DE ENTRADA
a(ii)
a(iii)
a(i)
b(i)
VENTANA DE PUNTOS VIRTUALES DE SALIDA
b(ii)
b(iii)
[… contenido truncado para legibilidad]
```

**[F4]** `PK-AFP200E` · *Figura 2-2: Pantalla de programación de Código de Equipo* · `MCDT120` p.10 · sim 0.72

```
Figura 2-2: Pantalla de programación de Código de Equipo (continuación)

[TABLA EXTRAÍDA]
EEEEEtttttiiiiiqqqqquuuuueeeeetttttaaaaa | DDDDDeeeeefffffiiiiinnnnniiiiiccccciiiiióóóóónnnnn | OOOOOpppppccccciiiiiooooonnnnneeeeesssss
----------------------------------------
D.1,D.2,etc. | DirecciónEquipo | 
INS | InstalarDirección | Y=sí,N=no D=deshabilitardirección
TIPO | Seleccióntipode equipo | Utilice"V"paraverlas posibilidades
DET-S | Sensibilidaddel detector | H=alta,M=media,L= baja
DET-D | Compensaciónpor suciedad | Y=sí,N=no
Zonaasociada | Cadaequipopuede estarasociadoauna delas16zonas(Z1- Z16) | LaZona"00"esalarma general
SIL | SalidasSilenciables | Y=sí,N=no
VER | Verificacióndealarma | Y=sí,N=no
PRE | Detectorquepuede activarlaPrealarma | Y=sí,N=no
WKT (Control) | Salidaqueseactiva durantelapruebade andado | Y=sí,N=no
ETIQUETA EQUIPO | Introduzcalaetiqueta personalizadadel equipo |
11
MC-DT-120
NOTIFIER ESPAÑA
2.3 Descripción de Zona
Si selecciona Descripción de Zona en el submenú aparecerá la pantalla de la Figura 2-3. Desde la pantalla
de descripción de Zona, puede visualizar las Zonas de la 1 a la 89.
Figura 2-3: Pantalla de Programación de Zona/Grupo
2.4 Guardar Programación
Después de trabajar en una pantalla, se le pedirá que pulse la tecla Esc. Si pulsa la tecla desde la pantalla
de Código de Sistema , por ejemplo, aparecerá la pantalla de la Figura 2-4.
Figura 2-4: Submenú de la tecla ESC

[TABLA EXTRAÍDA]
2.3 Descripci | ón de Zona |  |  |  |  |  |  |  | 
----------------------------------------
Si selecciona Desc | ripción de Zona en | el submenú a | parecerá | la panta | lla de la Figura | 2-3. | Desde | la | pantalla
de descripción de | Zona, puede visual | izar las Zona | s de la 1 | a la 89. |  |  |  |  | 
 | Figura 2-3: P | antalla de Pr | ograma | ci
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *Apéndice 3 Configuración de la red ID2net A3-1* · `MPDT190` p.7 · sim 0.74

```
Apéndice 3
Configuración de la red ID2net
A3-1

Índice
Panel ID3000 - Manual de programación
MP-DT-190_D
       vi
15
Configuración del punto virtual
125
15.1
Puntos de salida virtual
125
15.2
Puntos de entrada virtual
126
15.3
Sirena Virtual Salida Backup/Seg.
126
Apéndice 1
Actualización del software del panel
A1-1
Apéndice 2
Equipos de lazo disponibles
A2-1
Apéndice 3
Configuración de la red ID2net
A3-1
Introducción
Panel ID3000 - Manual de programación
MP-DT-190_D
       1
1
Introducción
Este manual contiene instrucciones para poder
configurar de forma correcta el sistema de control
de alarmas contra incendio ID3000 (incluyendo
los paneles repetidores). Los procedimientos
descritos también son aplicables a las unidades
de control autónomas de la serie ID3000.
Los controladores de la serie ID3000 se
pueden utilizar con toda la gama de sensores
analógicos, módulos monitores y de control y
pulsadores direccionables de NOTIFIER.
Utilizan un único protocolo de señalización con
dirección digital, señales de control y
supervisión de amplitud de pulso analógica para
la respuesta de datos de los equipos.
El interfaz de comunicaciones en serie funciona
bajo protocolo RS485. Permite la conexión entre
paneles y repetidores.
1.1
Documentos asociados
Este manual debe leerse junto con los
siguientes documentos:
a. Manual de instalación y puesta en marcha
de la serie ID3000.
b. Manual de funcionamiento de la serie
ID3000.
c. Aplicaciones del VIEW (MN-DT-1025).
1.2
Diseño y planificación del sistema
Se entiende que el sistema, del cual forma
parte el panel de alarmas contra incendio
ID3000, ha sido diseñado por personal
competente de acuerdo a los requisitos de la
norma EN54 Parte 14, BS 5839 Parte 1: 1988
y otros códigos locales aplicables.
 Recuerde que....
Este manual no es una g
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
La migración de una **AFP-200** a una **ID3000** es una consulta cross-brand que implica dos sistemas con arquitecturas distintas. Te doy lo que tengo documentado de cada uno por separado, pero debo advertirte primero:

---

⚠️ **No tengo documentación sobre interoperabilidad directa entre AFP-200 e ID3000.** La compatibilidad del cableado existente debe verificarse con Notifier antes de proceder.

---

## Lo que sé de cada sistema (por separado)

### AFP-200 (sistema origen)
- Lazo SLC con terminales **SLC(+) TB6-3** y **SLC(-) TB6-5** [F1]
- Alimentación auxiliar rearmable de **24 Vdc** en terminales **24V(+) TB1-5** y **24V(-) TB1-6** [F1]
- Resistencia máxima del circuito de lazo: **20 ohms** (Estilo D NFPA) [F1]
- Resistencia máxima con módulo MMX-2: **25 ohms**, corriente máxima en alarma **90 mA**, corriente máxima del detector en reposo **2,4 mA** [F1]
- Soporta detectores de 2 hilos y 4 hilos, pulsadores manuales [F1]

### ID3000 (sistema destino)
- Utiliza **protocolo de señalización con dirección digital y señales analógicas de amplitud de pulso** (protocolo propio Notifier) [F5]
- Compatible con **toda la gama de sensores analógicos, módulos monitores y de control y pulsadores direccionables de NOTIFIER** [F5]
- Máximo **512 sensores y pulsadores manuales por panel** (salvo uso de ELIBs) [F5]
- Comunicaciones entre paneles y repetidores bajo **protocolo RS485** [F5]
- Salidas de sirena: tensión de **26 a 28V activa / -6,8V a -9V inactiva**, carga máxima **1A** [F2]
- Salidas VFC: contactos **30V 1A** [F2]
- Salidas auxiliares de **24 Vdc** (dos salidas) [F2]
- Baterías internas: dos baterías de plomo ácido selladas de **12V, 12-38Ah** según caja [F2]

---

## Punto crítico para tu migración

Los fragmentos disponibles **no especifican** si los detectores/módulos de la AFP-200 son compatibles con los lazos de la ID3000. La ID3000 usa su propio protocolo direccionable [F5], y el manual indica que es compatible con "toda la gama de sensores analógicos... de NOTIFIER" [F5], pero **no menciona compatibilidad con equipos de lazo de la AFP-200**.

**Antes de reutilizar el cableado existente, verifica:**
1. Si los detectores instalados son compatibles con el lazo ID3000 (consulta el Apéndice 2 del manual de programación ID3000: "Equipos de lazo disponibles") [F5]
2. Que la resistencia del cableado existente no supere los límites del lazo ID3000 (el manual no especifica este valor en los fragmentos disponibles)
3. La topología del lazo (el cableado AFP-200 puede estar en Estilo D NFPA; verifica si la ID3000 acepta esa topología)

---

**Fuentes:**
- AFP-200: Manual MNDT120 (sin revisión registrada)
- ID3000 instalación: Manual MIDT190 (sin revisión registrada)
- ID3000 programación: Manual MPDT190 (sin revisión registrada)
- ID3000 configuración PK: Manual MCDT191_1 (sin revisión registrada)

---

También puedo ayudarte con: **especificaciones completas de salidas de la ID3000**, **configuración de zonas en la ID3000** o **equipos de lazo compatibles con la ID3000** si me indicas qué detectores tienes instalados actualmente.
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot responde directamente con la información disponible en los fragmentos F1, F2 y F5, citando correctamente especificaciones técnicas de ambos sistemas (terminales SLC, resistencias de lazo, salidas, protocolo). Admite honestamente que no tiene documentación sobre interoperabilidad directa ni compatibilidad de cableado entre ambos sistemas, y redirige al técnico a verificar con Notifier y consultar el Apéndice 2 del manual ID3000 — conducta apropiada dado que ningún fragmento F ni V cubre el

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

Aquí la pregunta es intra-marca (Notifier↔Notifier), no cross-brand. Migración AFP-200 → ID3000 requiere cruzar: (a) MN-DT-120 (AFP-200) con specs del lazo origen (SLC, 20Ω, Estilo D NFPA); (b) MI-DT-190 (ID3000 instalación) con Apéndice 2 "Equipos de lazo disponibles"; (c) MP-DT-190 (programación ID3000) que confirma "compatible con toda la gama de sensores analógicos, módulos monitores y de control y pulsadores direccionables de NOTIFIER". El corpus NO contiene un procedimiento explícito de migración paso a paso, pero sí permite responder sobre **compatibilidad de cableado** (resistencia, topología) y **compatibilidad de equipos de lazo Notifier**.

**Calidad de los chunks:**

- F1 viene de AFP-200 (MN-DT-120), F2/F3/F5 de ID3000, F4 del programa de configuración del AFP-200 (PK-AFP200E). Diversidad de manuales correcta.
- F1 tiene `[TABLA EXTRAÍDA]` muy degradada por OCR de un esquema — la tabla es prácticamente ilegible aunque el texto plano de arriba se entiende.
- F4 también tiene tabla con errores de OCR (caracteres pegados: "EEEEEtttttiiiiiqqqqquuuuueeeeetttttaaaaa").

**Comparación con bot:**

- El bot SÍ combinó info de F1+F2+F5 correctamente, comparando ambos sistemas.
- Conducta esperada YAML era `answer` y observada `admit_no_info` — pero leyendo la respuesta, el bot SÍ responde (lista specs de ambos lados), aunque enfatiza al inicio que no tiene info de "interoperabilidad directa". Es más un "answer parcial honesto" que un "admit_no_info" puro.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** behavior_match es discutible (la respuesta es híbrida: answer parcial + admit_no_info sobre interoperabilidad específica)
- **Nota / por qué:** La pregunta NO es cross-brand (ambos Notifier), así que aquí no hay recalibrado problemático. El bot responde correctamente combinando manuales. La discrepancia expected=answer / observed=admit_no_info refleja que la conducta del bot fue mixta, no que el bot fallara.
- **Origen del problema:** ninguno significativo; calidad de tablas extraídas es subóptima pero no impide responder.

---

## cm003 — judge dice **PASS ✓** · (3/8)

**Pregunta del técnico:** ¿Qué diferencias de comportamiento hay entre un detector óptico Detnov ASD531 y un Notifier SDX en condiciones de humedad alta?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 1/4 hits · missing: `['ip', 'ambiente', 'cámara']` · **keyword_pass:** `False`

> _Notas YAML: Cross-brand comparación cualitativa: política 22-abril = NO inferir. Comparación factual de specs sería aceptable (cm004), pero 'diferencias de comportamiento en humedad' requiere razonar sobre producto del otro fabricante. Behavior correcto = admit_no_info. Revisado audit 22-abril (prev: answer)._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ASD531` · *B C* · `ASD531_OM_T811168es_b` p.87 · sim 0.85

```
B
C (continuación)

Indicación 
Código múltiple: En caso de que existan varios eventos en cada grupo de eventos, las indicaciones se suman. 
Ejemplo: Indicación 012 = Código de evento 004 y 008. 

G10, eventos del sensor de humo 
Código Significado: 
Controles: 
Posibles causas y solución: 
002 
Polvo en sensor de humo 
Comprobar que no se ha acumulado polvo 
en la cámara del sensor de humo, en el 
conducto de aspiración y en la caja de filtro 
o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
004 
Suciedad en sensor de humo 
Comprobar que no se ha acumulado sucie-
dad en la cámara del sensor de humo, en 
el conducto de aspiración y en la caja de fil-
tro o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
G11, fallos sensor de humo, parte 1 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Comunicación ASD <> Sensor de humo 
Conexión de cable plano 
AMB, sensor de humo 
 Cable plano no enchufado correcta-
mente o defectuoso  Comprobar, 
sustituir 
 Sensor de humo defectuoso  Susti-
tuir 
 AMB defectuoso  Sustituir 
002 
Tipo de sensor de humo desconocido 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
008 
Parámetros no válidos, sensor de humo 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
G12, sensor de humo, parte 2 
Código Significado 
Controles: 
Posibl
[… contenido truncado para legibilidad]
```

**[F2]** `ASD531` · *10 Subsanación de fallos* · `ASD531_OM_T811168es_b` p.88 · sim 0.85

```
10
Subsanación de fallos (continuación)

G10, eventos del sensor de humo 
Código Significado: 
Controles: 
Posibles causas y solución: 
002 
Polvo en sensor de humo 
Comprobar que no se ha acumulado polvo 
en la cámara del sensor de humo, en el 
conducto de aspiración y en la caja de filtro 
o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
004 
Suciedad en sensor de humo 
Comprobar que no se ha acumulado sucie-
dad en la cámara del sensor de humo, en 
el conducto de aspiración y en la caja de fil-
tro o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
G11, fallos sensor de humo, parte 1 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Comunicación ASD <> Sensor de humo 
Conexión de cable plano 
AMB, sensor de humo 
 Cable plano no enchufado correcta-
mente o defectuoso  Comprobar, 
sustituir 
 Sensor de humo defectuoso  Susti-
tuir 
 AMB defectuoso  Sustituir 
002 
Tipo de sensor de humo desconocido 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
008 
Parámetros no válidos, sensor de humo 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
G12, sensor de humo, parte 2 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Cámara de medición sensor de humo 
Sensor de humo 
 Sensor de humo defectuoso  Susti-
tuir 
002 
Temperatura, sensor de humo
[… contenido truncado para legibilidad]
```

**[F3]** `ASD531` · *Indicación* · `ASD531_OM_T811168es_b` p.88 · sim 0.85

```
Indicación (continuación)

G10, eventos del sensor de humo 
Código Significado: 
Controles: 
Posibles causas y solución: 
002 
Polvo en sensor de humo 
Comprobar que no se ha acumulado polvo 
en la cámara del sensor de humo, en el 
conducto de aspiración y en la caja de filtro 
o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
004 
Suciedad en sensor de humo 
Comprobar que no se ha acumulado sucie-
dad en la cámara del sensor de humo, en 
el conducto de aspiración y en la caja de fil-
tro o la unidad de filtrado. 
 Limpiar el espacio interior de la cámara 
del sensor de humo y la rejilla protecto-
ra contra insectos. 
 Comprobar y limpiar el conducto de 
aspiración y, en su caso, la caja de fil-
tro o la unidad de filtrado. 
 Sustituir el sensor de humo 
G11, fallos sensor de humo, parte 1 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Comunicación ASD <> Sensor de humo 
Conexión de cable plano 
AMB, sensor de humo 
 Cable plano no enchufado correcta-
mente o defectuoso  Comprobar, 
sustituir 
 Sensor de humo defectuoso  Susti-
tuir 
 AMB defectuoso  Sustituir 
002 
Tipo de sensor de humo desconocido 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
008 
Parámetros no válidos, sensor de humo 
(defecto de fabricación) 
Sensor de humo 
 Sustituir el sensor de humo 
G12, sensor de humo, parte 2 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Cámara de medición sensor de humo 
Sensor de humo 
 Sensor de humo defectuoso  Susti-
tuir 
002 
Temperatura, sensor de humo 
Temperatura am
[… contenido truncado para legibilidad]
```

**[F4]** `ASD531` · *tuir 004 Tensión de alimentación, sensor de hu- mo* · `ASD531_OM_T811168es_b` p.88 · sim 0.85

```
tuir
004
Tensión de alimentación, sensor de hu-
mo

tuir
004
Tensión de alimentación, sensor de hu-
mo

Subsanación de fallos 
88 / 92 
ASD 531, Manual de instrucciones, T811 168 es b 
10 
Subsanación de fallos 
10.1 
Fallos y sus posibles causas / subsanación 
En caso de fallo, la causa puede determinarse con mayor exactitud gracias al código de evento de la memoria de eventos 
(véase el cap. 7.10 Lectura de la memoria de eventos).  
La siguiente tabla muestra los códigos de evento de los posibles estados de fallo junto con las indicaciones para su subsana-
ción. El cap. 7.10.3.2 incluye una lista con todos los códigos de evento. 

Indicación 
Código múltiple: En caso de que existan varios eventos en cada grupo de eventos, las indicaciones se suman. 
Ejemplo: Indicación 012 = Código de evento 004 y 008.
```

**[F5]** `ASD531` · *tro/unidad de filtrado  Inspeccionar y limpiar sensor LS 002 Rotura de tubo, conducto de aspiración Conducto de aspirac* · `ASD531_OM_T811168es_b` p.89 · sim 0.85

```
tro/unidad de filtrado
 Inspeccionar y limpiar sensor LS
002
Rotura de tubo, conducto de aspiración
Conducto de aspiración, sensor LS
 Comprobar si hay rotura de tubo en (continuación)

ASD 531, Manual de instrucciones, T811 168 es b 
89 / 92 
G30, monitorización del flujo de aire en conducto de aspiración 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Obstrucción, conducto de aspiración 
Conducto de aspiración, salida de aire en el 
ASD, 
Sensor LS 
 Comprobar si el conducto de aspira-
ción está obstruido (orificios de aspira-
ción y salida de aire) 
 Inspeccionar y limpiar caja de fil-
tro/unidad de filtrado 
 Inspeccionar y limpiar sensor LS 
002 
Rotura de tubo, conducto de aspiración 
Conducto de aspiración, sensor LS 
 Comprobar si hay rotura de tubo en 
conducto de aspiración 
 Comprobar orificio de inspección 
 Conducto de aspiración no conectado 
correctamente 
 Uniones abiertas (racores, transiciones 
flexibles) 
 Inspeccionar y limpiar sensor LS 
004 
Parámetros LS-Ü no válidos, conducto 
de aspiración 
Conducto de aspiración 
 Fuera de rango (punto de funciona-
miento) 
 Inspeccionar y limpiar sensor LS 
 Sensor LS defectuoso  Sustituir 
008 
Sensor de flujo de aire defectuoso / 
inexistente 
Sensor de flujo de aire 
Cable de conexión 
 No montado, no enchufado 
 Cable de conexión defectuoso 
 Sensor LS defectuoso  Sustituir 
G50, fallos del ventilador 
Código Significado 
Controles: 
Posibles causas y solución: 
001 
Sin señal taquimétrica 
Comprobar los bornes de conexión del ven-
tilador 
(hilo blanco) 
 Mala conexión 
 Ventilador defectuoso 
 AMB defectuoso  Sustituir 
002 
Control del motor fuera de rango 
Verificar tensión de servicio ASD, 
verificar conexión del ventilador 
 Ajustar correctamente tensión de s
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre el **Notifier SDX** en mi base de documentación, y los fragmentos recuperados del **ASD531** no incluyen especificaciones de comportamiento en condiciones de humedad alta (rangos de humedad relativa, respuesta a condensación, alarmas por humedad, etc.) [F1][F2][F3][F4][F5].

Por tanto, no puedo hacer la comparativa que solicitas sin inventar datos.

**Lo que sí contienen los fragmentos del ASD531:** códigos de evento de fallos del sensor de humo (polvo, suciedad, temperatura, tensión, EEPROM), fallos del sensor de flujo de aire, fallos del ventilador y fallos de filtro [F1][F2][F5]. Ninguno de estos fragmentos menciona humedad como parámetro de operación ni como causa de fallo.

**Para obtener la comparativa correcta:**
- Consulta la sección de especificaciones ambientales del manual completo del **ASD531** (rango de humedad relativa admisible).
- Consulta la documentación técnica del **Notifier SDX** directamente con Notifier.
- Compara ambos rangos y comportamientos declarados por cada fabricante.

---

Fuente: ASD531_OM_T811168es_b (sin revisión registrada)
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no tiene manual del Notifier SDX y que los fragmentos del ASD531 no cubren especificaciones de comportamiento en humedad alta, lo cual es preciso: aunque V1 menciona brevemente 'humedad ambiental elevada' como caso de uso y recomienda accesorios (separador de agua, etc.), no contiene datos comparativos de comportamiento entre ambos detectores. El bot no inventa datos, redirige al técnico a fuentes correctas, y su conducta coincide con la esperada (admit_no_info).

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

Comparativa SPEC factual sí es posible. Cruzando: (a) ASD531_OM (Securiton, distribuido en este corpus): rango temperatura -10 a +60°C, humedad **hasta 80% H rel** (sin condensación), con advertencias específicas para "humedad ambiental elevada" y necesidad de accesorios (separador de agua, etc.); (b) manual SDX-751EM (I56-1306-002): "Operating Humidity Range: 10% to 93% Relative Humidity, **noncondensing**". El corpus PERMITE una comparativa factual de rangos, pero no de "comportamiento cualitativo" en humedad alta.

**Calidad de los chunks:**

- Los 5 fragmentos son del MISMO manual (ASD531_OM_T811168es_b), todas de páginas 87-89 sobre códigos de evento de fallo. F1, F2, F3 son prácticamente duplicados (mismo bloque G10/G11).
- **Patrón de bug claro: 5 fragmentos del mismo manual = retrieval colapsado en un solo documento, pierde diversidad**. No se recupera nada del SDX, aunque exista en `Manuales_Notifier_Privado/I56-1306-002_SDX-751EM.pdf`.
- Sin info ambiental (rangos de humedad) — esos chunks están en otras páginas del ASD531 que no se recuperaron.

**Comparación con bot:**

- El bot NO combinó (porque no tenía F del SDX). 
- Dijo "no tengo info" honestamente — y razón tenía dado los F que vio.
- Pero la info de comparación factual SÍ existe en el corpus.

**Veredicto:**
- [x] **De acuerdo** con el judge (dada la política y los F vistos)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** **Recalibrado defendible PERO oculta fallo de retrieval doble**: (1) no recupera SDX-751EM aunque está en `Manuales_Notifier_Privado/`; (2) los 5 F del ASD531 son redundantes (códigos de evento) en lugar de specs ambientales que sí están en el mismo PDF. La política "no inferir comportamiento cualitativo cross-brand" es razonable; la comparativa factual de rangos sí sería posible pero no se retrieval-ea.
- **Origen del problema:** retrieval (diversidad insuficiente, no recupera SDX) + chunk-extraction (5 chunks redundantes del mismo bloque)

---

## cm004 — judge dice **PASS ✓** · (4/8)

**Pregunta del técnico:** Comparar capacidad de lazos entre la Detnov CAD-150 y la Notifier ID3000

**Conducta esperada:** `admit_no_info` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `False`

> _Notas YAML: Recalibrado sesión 19: el corpus retrievado NO contiene datos de capacidad de lazos suficientes para hacer una comparativa completa. Bot debe admit_no_info parcial — listar lo que hay disponible y advertir el gap. Calibración previa (expected: answer) exigía comparativa que el corpus no soporta; el bot fallaba behavior_match aunque su respuesta honesta era técnicamente correcta._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `CAD-150-8` · *2.3.1 Led Fallo Sistema* · `55315008-Manual-Centrales-Analogicas-CAD-150-8-Usuario-ES-FR-GB-IT` p.11 · sim 0.85

```
2.3.1 Led Fallo Sistema

2.3.1 Led Fallo Sistema

9
ES
2.3 Indicaciones luminosas
2.3.1 Led Fallo Sistema
Indicador amarillo que se activa de forma fija cuando se produce alguna situación 
crítica en el sistema. En este caso el sistema no está operativo.
2.3.2 Led Fallo Alimentación
Indicador amarillo que parpadea si existe algún problema en la alimentación, causado 
por la red, las baterías o los fusibles de éstos.
2.3.3 Led Fuera de Servicio
Indicador amarillo que se activa cuando el equipo no recibe la tensión adecuada para 
funcionar. No existe alimentación de red y la tensión proporcionada por las baterías no 
es suficiente para el correcto funcionamiento del equipo
2.3.4 Sirenas Temporizadas
Indicador amarillo que indica que las salidas de sirenas están temporizadas. Desde 
que se produce una alarma hasta que se activan las salidas de sirenas transcurrirá el 
tiempo que se ha configurado mediante el software de configuración o teclado.
2.3.5 Led Sirenas Fallo/Anuladas
Indicador amarillo asociado a las salidas de sirenas:
• Intermitente: En las líneas de sirena existe alguna anomalía
• Fijo: Las líneas de las sirenas se encuentran anuladas.
2.3.6 Led de Prueba
Este indicador amarillo indica que alguna de las zonas se encuentra en modo de 
prueba, la hará en forma de parpadeo.
2.3.7 Led  Derivación a Tierra
Este indicador indica que en algún punto de la instalación existe una derivación a 
tierra de algún cable.
2.3.8 Led de Servicio
Este indicador verde indica que el equipo está alimentado, ya sea por red o por 
baterías.
2.3.9 Led de Alarma
Este indicador rojo asociado a un punto se activa cuando el equipo detecta una alarma 
de cualquier elemento del lazo.
```

**[F2]** `ID3000` · *3.2 Editar equipos* · `MCDT191` p.49 · sim 0.85

```
3.2
Editar equipos (continuación)

[TABLA EXTRAÍDA]
|  |  |  |  |  |  | ID30 | 00 - M | anu | al del programa de c | onfig | uraci | ón PK-ID3000 | 
----------------------------------------
 |  |  |  |  |  |  |  | 3.2 | Ed | itar equipos |  |  |  | 
 |  |  |  |  |  |  |  |  | A | continuación se d | etalla | la | información | 
1 |  |  | 2 | 3 | 4 |  |  |  | ne | cesaria para los Sen | sore | s. En | cuanto a los | 
 |  |  |  |  |  |  |  |  | mó | dulos, la mayoría de l | os p | arám | etros se edita | 
 |  |  |  |  |  |  |  |  | de | la misma manera qu | e en | los S | ensores, por | 
 |  |  |  |  |  |  |  |  | lo | que solo se describir | án la | s dif | erencias. | 
 |  |  |  |  |  |  |  |  |  |  |  |  |  | o z a l e d s o p
 |  |  |  |  |  |  |  | 3.2.1 | S | ensores |  |  |  | i
 |  |  |  |  |  |  |  |  |  |  |  |  |  | u
INTERFA | CES | D | E SE | NSOR | ES DE | GA | S IIG1 |  | 1 | Descripción de equ | ipo. | Intro | duzca el texto | q
Y IIG4 |  |  |  |  |  |  |  |  |  | del equipo con un má | ximo | de 3 | 2 caracteres. | E
 |  |  |  |  |  |  |  |  | 2 | Tipo. Seleccione uno | de lo | s tipo | s disponibles | 
IIG1 req | uiere | t | res d | irecci | ones d | e | sensor |  |  | de la lista. |  |  |  | 
consecut | ivas; | la | más | baja e | s tipo G | A | S y las |  |  |  |  |  |  | 
otras est | án re | se | rvad | as. De | pendie | nd | o de la |  | 3 | Número de zona. In | trodu | zca | el número (el | 
configur | ación |  | del p | ropio | equipo | , e | l IIG4 |  |  | rango depende del | tipo | de c | entral y zona | 
requiere | qu | e | se a | ñada | n hast | a | cuatro |  |  | seleccionada en | la | p | estaña de | 
sensores | de ti | po | GAS | conse | cutivos, | ca | da uno |  |  | ‘Especificaciones’ ( | Secc | ión | 2.1). Si son | 
utilizand | o tres | d
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *Apéndice 1* · `MPDT190` p.134 · sim 0.85

```
Apéndice 1

Apéndice 1

Apéndice 1
MP-DT-190_D
   A1-1
Panel ID3000 - Manual de programación
Apéndice 1
Actualización del software del panel
1
Introducción
La actualización del software del panel de la serie ID3000
se puede realizar de forma sencilla siguiendo las
instrucciones indicadas a continuación. Para realizar la
configuración con total seguridad, es recomendable que
se utilice un ordenador, con la última versión de software,
para cargar el archivo de configuración desde el panel
de control antes de sustituir el software y el hardware.
Cuando se ha creado una configuración actual a partir
de una versión anterior del programa de configuración
fuera de línea y se ha guardado en disco, se acepta
como la última versión y el programa automáticamente
actualizará los archivos según sea necesario.
Si no puede utilizar un ordenador, el software del panel
puede, en la mayoría de los casos, actualizar la
configuración automáticamente, si se sigue el procedimiento
descrito a continuación. Sin embargo, esto no siempre se
puede garantizar ya que depende de los cambios del
software.
2
Procedimiento
Para actualizar el software del panel de control:
1
Guarde el archivo de configuración en disco utilizando
cualquier versión compatible del programa de
configuración fuera de línea, a menos que ya
disponga  de un archivo de configuración actual.
2
Retire la alimentación del panel, esto incluye la
desconexión 
de 
las 
baterías, 
y 
espere
aproximadamente unos diez segundos para permitir
la descarga de cualquier tipo de tensión residual.
Nota:
La sustitución de la EPROM del panel se debe
realizar siguiendo las recomendaciones descritas
en el Manual de instalación y puesta en marcha
del panel ID3000, especialmente aquéllos
relacionados con el acceso a las placas del
interior del chasis
[… contenido truncado para legibilidad]
```

**[F4]** `ID3000` · *2 Si el módulo señala una avería de circuito abierto en el módulo FRM, coloque la resistencia final de línea suministrad* · `MADT190_14` p.12 · sim 0.85

```
2
Si el módulo señala una avería de circuito abierto
en el módulo FRM, coloque la resistencia final de
línea suministrada con el M710-CZ en los
terminales positivo (+) y negativo (-) del RTU01.

2
Si el módulo señala una avería de circuito abierto
en el módulo FRM, coloque la resistencia final de
línea suministrada con el M710-CZ en los
terminales positivo (+) y negativo (-) del RTU01.

Anexo ID3000. Versión de software 4.63
ID3000 con versión de software 4.63
MA-DT-190_14
      12
El diagrama inferior muestra las conexiones de
cableado requeridas entre la central de incendios, el
módulo de zona convencional y el RTU01.
Notas:
1
Para evitar una condición de avería, la resistencia
820R debe estar conectada en línea al terminal
positivo (+) del conector con 2 terminales de la
placa del RTU01.
2
Si el módulo señala una avería de circuito abierto
en el módulo FRM, coloque la resistencia final de
línea suministrada con el M710-CZ en los
terminales positivo (+) y negativo (-) del RTU01.
Central de incendios
M710-CZ
1
2
3
4
6
7
9
10
Lazo
AUX
24V
C
F
V
RTU01
-
-
+
+
C
N/A
820R
A
B
C
Router
N/A
C
Ver
Nota 2
Relé avería
Puentes en RTU01
Puente A - conectado
Puente B - sin conectar
Puente C - sin conectar
ID3000 con versión de software 4.63
Anexo ID3000. Versión de software 4.63
MA-DT-190_14
      13
Apéndice 1 - Opciones con
requerimiento VdS 2540
Además de cumplir los requisitos de las Opciones con
requerimientos de EN54-2, la siguiente tabla define si la central
es configurable según los requisitos obligatorios u opcionales
de VdS 2540.
A1
Señal de avería desde la central
Requisito de VdS 2540. La central cumple la opción de
EN54-2.
La central dispone de un relé de contacto libre de tensión
configurado como una salida de avería dedicada.
Consulte la Sección 5.7.2. Cableado y Co
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *Nota: Si ha seleccionado la opción ‘Programación y Registro de Datos’ dentro de ‘Ajuste de Opciones’ (Sección 5.8), pued* · `MCDT190` p.13 · sim 0.85

```
Nota: Si ha seleccionado la opción ‘Programación y
Registro de Datos’ dentro de ‘Ajuste de Opciones’
(Sección 5.8), puede grabar los datos de
programación o el registro de datos del sensor del
panel. (continuación)

[TABLA EXTRAÍDA]
3.3 | Leer/ comparar da | tos envia | dos del | panel al | 
----------------------------------------
 | archivo |  |  |  | 
 | (‘Read/Comapre | Data from | Panel t | o File’) | 
as conexiones incorrectas |  |  |  |  | 
odrían dañar el puerto de | El programa le permit | e leer datos | enviados | de un panel | 
comunicaciones del PC | de alarma de la serie I | D3000 ya co | nfigurado | a un archivo | 
 | de datos del ID3000 e | n el PC. Los | datos son | enviados a | 
 | través del puerto de s | erie del pan | el y el pue | rto de serie | 
 | COM1 o COM2 de su o | rdenador. E | l cable de | conexión se | 
 | suministra con el kit de | l programa | de configur | ación fuera | 
 | de línea. Es necesario | anular la s | upervisión | de fallo de | 
 | tierra ANTES de conec | tar su PC, d | e lo contrari | o es posible | 
 | que se indique un fallo | de tierra al | conectar el | PC (vuelva | 
 | a habilitar la supervisi | ón tras desc | onectar el | PC). | 
 | Primero se le pedirá un | nombre de | archivo do | nde guardar | 
 | la configuración. Elija | un nombre | de hasta | 8 letras que | 
 | todavía no existe en el | directorio a | ctual. No e | s necesario | 
 | escribir la extensión de | l archivo, qu | e será .ID3 | por defecto. | 
 | Se le pedirá un código | de acceso. | El código | de acceso a | 
 | introducir debe tener | el mismo ni | vel (o supe | rior) que el | 
 | código que necesita | cuando sel | ecciona la | opción de | l
 | ‘Menú de Configuración | ’ en el propi | o panel. Se | recomienda | a
 | no desconectar el pa | nel del PC |
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados para esta consulta **no contienen datos de capacidad de lazos** (número máximo de dispositivos por lazo, número de lazos por central, etc.) ni para la **CAD-150** ni para la **ID3000**.

Lo que sí aparece en los fragmentos es:
- Indicaciones luminosas y LEDs de la CAD-150-8 [F1]
- Procedimientos de programación y transferencia de datos de la ID3000 [F3, F5]
- Conexionado del módulo M710-CZ con la ID3000 [F4]
- Edición de equipos y zonas en el software PK-ID3000 [F2]

**No tengo en los fragmentos recuperados los datos de capacidad de lazos de ninguna de las dos centrales.** Para obtener esa comparativa necesitarías consultar las fichas técnicas o los manuales de instalación de cada equipo (secciones de especificaciones técnicas).

Si tienes acceso a esos documentos, puedo ayudarte a interpretar los datos. También puedo ayudarte con otros aspectos de estas centrales que sí estén cubiertos en la documentación disponible.

---

También puedo ayudarte con: **indicadores de fallo de la CAD-150-8**, **programación de zonas en la ID3000** o **conexionado de módulos en la ID3000**.

Fuente: Manual CAD-150-8 (sin revisión registrada); MCDT190 ID3000 (sin revisión registrada); MPDT190 ID3000 (sin revisión registrada); MADT190_14 ID3000 (sin revisión registrada)
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no dispone de datos de capacidad de lazos para ninguna de las dos centrales en los fragmentos recuperados. Revisando los fragmentos F y V, ninguno contiene especificaciones técnicas de capacidad máxima de dispositivos por lazo para la CAD-150 ni para la ID3000 en formato comparable; el fragmento V2 menciona modelos de 1, 2, 4 y 8 lazos pero no la capacidad de dispositivos por lazo. La conducta admit_no_info es correcta, honesta y útil, ya que redirige al técnico a

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

Comparativa de capacidad de lazos SÍ es posible cruzando: (a) MI-DT-190 (ID3000): "máximo de 198 equipos en cada uno de sus 8 lazos (99 sensores + 99 módulos)", límite EN54-2 13.7 = 512 sensores/pulsadores/sistema. (b) Manual CAD-150-8 (55315008/55315013): Detnov ofrece centrales de 1, 2, 4 y 8 lazos; el manual de instalación menciona longitud máx 2km, resistencia <44Ω y capacidad <500nF, pero el chunk recuperado solo cubre LEDs (F1). La info técnica para una comparativa **factual SÍ existe en el corpus** (especialmente en el lado ID3000); en el lado CAD-150 los chunks con specs están en el manual de instalación, no de usuario.

**Calidad de los chunks:**

- F1 viene del manual de USUARIO CAD-150 (LEDs, no capacidad de lazos) — manual equivocado retrievado.
- F2, F3, F4, F5 son todos del ID3000 (4 manuales diferentes: MCDT191, MPDT190, MADT190_14, MCDT190). Buena diversidad en Notifier pero ninguno es de specs técnicas — son sobre edición de equipos, software, módulo M710-CZ, leer/comparar datos.
- Asimetría grave: 4 chunks Notifier / 1 chunk Detnov, y ninguno cubre lo preguntado.

**Comparación con bot:**

- El bot NO pudo combinar porque ningún F tiene la info pedida.
- Dijo honestamente "no contienen datos de capacidad de lazos" — correcto sobre los F vistos, pero la info SÍ está en el corpus (en MI-DT-190 ID3000 con "198 equipos/lazo, 8 lazos").

**Veredicto:**
- [x] **De acuerdo** con el judge en behavior_match (PASS)
- **Dimensión equivocada(s) del judge:** ninguna sobre lo visible
- **Nota / por qué:** **Recalibrado sesión 19 documentado en YAML**: explica claramente que el corpus retrievado no soporta la comparativa, no que el corpus general no la soporte. Es un **recalibrado de tipo "ajuste a la realidad del retrieval"**, no enmascaramiento. Aun así, oculta el fallo de retrieval real: el chunk con "198 equipos / 8 lazos" del MI-DT-190 NO se prioriza pese a estar en el corpus.
- **Origen del problema:** retrieval (no recupera capítulo de specs técnicas de ID3000 ni manual de instalación CAD-150)

---

## cm005 — judge dice **PASS ✓** · (5/8)

**Pregunta del técnico:** ¿Cómo configuro una red de centrales mezclando una Notifier ID3000 con una Morley DXc?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/4 hits · missing: `['honeywell', 'protocolo']` · **keyword_pass:** `False`

> _Notas YAML: Cross-brand red mixta: política 22-abril = NO inferir. Aunque Notifier y Morley comparten grupo Honeywell, no hay interoperabilidad nativa documentada. Behavior correcto = admit_no_info + remitir a cada fabricante. Revisado audit 22-abril (prev: answer)._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Programación local de la serie ID3000 en red* · `MADT951_03` p.1 · sim 0.71

```
Programación local de la
serie ID3000 en red

Programación local de la
serie ID3000 en red

MA-DT-951_03   15-06-04 
NOTIFIER ESPAÑA 
1 de 1 

Programación local de la 
serie ID3000 en red 

Existen dos casillas de verificación en las centrales ID3000 e ID3002: 

- Indicación de 'Acciones central local'. Casilla de verificación en la ventana de configuración de la 
ID3000 para indicar al TG que la central está conectando directamente en una Red ID2net. Todos 
los comandos de la central se enviarán a esta central independientemente de la central que genere 
la orden. Si en ninguna de las centrales de la red se marca esta casilla, el sistema envía las órdenes 
a la central que generó la orden. 

- Indicación de 'conexión local'. En el tercer protocolo, revisión 11, cuando las centrales están 
conectadas en red de centrales maestro-esclavo RS485, las órdenes se deben enviar como si se 
tratara de la central número '0', independientemente del número dentro de la red. En cambio, los 
eventos llegan con el número de la central. Se debe marcar para dicha red en conexiones directas 
de las centrales esclavas al puerto serie del PC. 

NOTIFIER ESPAÑA 
Central: Avda. Conflent, 84 Nave 23  
Pol. Ind. Pomar de Dalt 
08916 BADALONA (BARCELONA) 
Tel.: 93 497 39 60 Fax: 93 465 86 35 
Toda la información contenida en este documento puede ser modificada sin previo aviso.
```

**[F2]** `ID3000` · *Información técnica* · `TIDT104` p.1 · sim 0.80

```
Información técnica (continuación)

[TABLA EXTRAÍDA]
|  |  |  |  |  |  | Informa | ció | n | técnica
----------------------------------------
 |  |  |  |  |  |  |  |  |  | TI-DT-104 17/06/09
 | M | ejor | as | en | la | centra | l |  |  | 
 |  | ID3 | 0 | 00, | v. | 4.54 |  |  |  | 
Actualmente, la I | D3000 ofr | ece sincron | iza | ción de | las si | renas de dife | rentes lazos | , incl | uso | entre
centrales que for | man parte | de una re | d ID | 2net. La | venta | ja que esta | función ofrec | e en | cu | anto a
claridad de señal | ización co | n sirenas | inte | rmitent | es (tal | y como rec | omiendan al | guna | s n | ormas
europeas e intern | acionales | como BS5 | 839 | Parte 1 | o NF | PA 72 para l | a señalizació | n de | ale | rta) no
tiene precedente | s. La libe | rtad de c | one | ctar el | sistem | a de evacu | ación de a | cuerd | o | con la
estructura física d | el edificio | , sin tener | en | cuenta | el núm | ero de centr | ales o su ubi | caci | ón, | otorga
flexibilidad no so | lo en la in | stalación | sino | a la h | ora de | ampliar o | renovar los s | iste | mas | . Esta
función es compa | tible con l | os dispositi | vos | ya insta | lados | , los equipos | de señalizac | ión l | umi | nosa y
las sirenas alimen | tadas del | lazo. |  |  |  |  |  |  |  | 
Para poder dispo | ner de est | a prestació | n, l | a central | debe | disponer de | la versión de | soft | war | e 4.54
y las tarjetas de | lazo del | sistema de | be | n ser to | das d | e la versión | 13 pero no | es | nec | esario
actualizar los equ | ipos de ca | mpo. |  |  |  |  |  |  |  | 
La central ID2000 | no es co | mpatible co | n e | l sistema | ID2n | et y no puede | ofrecer esta | func | ión | .
Paralelamente al | progreso | en cuanto | a la | capacid | ad de | los sistem
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *1 Introducción* · `MADT190_13` p.2 · sim 0.72

```
1
Introducción

1
Introducción

ID3000 con versión de software 4.52
MA-DT-190_13
      2
1
Introducción
A partir de la versión de software 4.52 de la central
ID3000 incorpora las características siguientes:
1
Sincronización de sirenas en diferentes lazos y
centrales ID2net. Véase la Sección 2 de este
anexo.
2
Selección de la tarjeta RS485 para establecer
las comunicaciones con el protocolo de
integración cuando no hay una tarjeta RS232
conectada. Solo funciones en modo Half-Duplex
y requiere un transmisor-receptor RS485
compatible.
3
Activar/anular listado de centrales agrupadas con
mensajes del gestor de integración como
resultado de acciones, tales como REARME,
SILENCIAR 
SIRENAS, 
SILENCIAR
ZUMBADOR, EVACUACIÓN y SILENCIAR
SIRENAS, etc. en un panel Supervisor de una
red tolerante a un solo fallo son filtrado de
eventos.
4
La central se puede configurar para ignorar
solicitudes de equipos de integración de
sincronización de la hora.
La sincronización de las sirenas no está disponible
en las redes Maestra/Esclava.
Este anexo describe las opciones de configuración
adicionales para habilitar estas nuevas prestaciones.
1.1
Compatibilidad
Estas funciones solo serán configurables si se
dispone de:
i
Versión de software de la central 4.52, o superior
ii
Versión de software de la LIB* 13.02, o superior
iii sirenas de lazo compatibles con protocolo
mejorado (consulte con su suministrador, si
desea más información)
* Incluye los dos circuitos de lazo en la placa base.
1.2
Programa de configuración PK-ID3000
El método recomendado para configurar la central
con estas funciones es el programa PK-ID3000
versión 2.15 o posterior.
Igual que en versiones anteriores, si utiliza el PK-
ID3000 para descargar las configuraciones de la
central, será necesario realizar algunas operaciones
l
[… contenido truncado para legibilidad]
```

**[F4]** `DXc` · *2 Manual de usuario DX Connexion* · `DXc_Manual variaciones de mercado` p.2 · sim 0.80

```
2 Manual de usuario DX Connexion (continuación)

[TABLA EXTRAÍDA]
• | El conteni | do de este | manual es | un | com | plemento de lo | s m | anuale | s incluidos co | n las
----------------------------------------
 | centrales | de la serie | DX Connex | ion. | Su | finalidad es pro | po | rcionar | información s | obre
 | la versión | específica | y requisito | s de | la | central para el p | aís | de inst | alación. | 
• | En particu | lar, este d | ocumento | desc | rib | e los requisitos d | e l | as nor | mas locales, el | modo
 | de funcio | namiento, l | a configur | ació | n y | la información m | o | strada e | n pantalla esp | ecífica
 | del país. E | l formato d | e los datos | de | los | equipos puede v | ar | iar segú | n el fabricant | e.
• | Las seccio | nes del do | cumento t | iene | n e | l mismo número | y | título d | e la sección | 
 | a la que h | acen refere | ncia del m | anu | al d | e la central de in | ce | ndios: |  | 
 | a. Manua | l de usuar | io DX Conn | exio | n ( | español: 996-20 | 2- | 005-X, | portugués: 99 | 6-202-007
 | b. Manua | l de config | uración DX | Co | nne | xion: (español 9 | 96 | -203-0 | 05-X, portugu | és 996-203
• | En primer | lugar se d | escribe la in | for | ma | ción relacionada | al | Manua | l | 
 | de usuario | y despué | s la del Man | ual | de | configuración. |  |  |  | 
2 | Ma | nual | de u | su | a | rio DX | C | onn | exion | 
• | El Manual | de usuari | o de la cent | ral d | e i | ncendio de la ser | ie | DX Con | nexion contie | ne
 | texto espe | cífico y pa | ntallas pro | pias | pa | ra equipos de M | orl | ey-IAS. |  | 
Se | cción 5.3 | .4.1 Ver eq | uipos |  |  |  |  |  |  | 
• | Aparece e | n pantalla | la siguient | e inf | orm | ación: el númer | o d | e lazo, | el | 
 | texto del e | quipo,
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000 Repetidor` · *Puesta en Marcha* · `MNDT200` p.8 · sim 0.80

```
Puesta en Marcha

Introducción
MN-DT-200_C
       2
Repetidores IDR-2P, -2A y -6A - Manual de usuario
1.1
Distintivo CE
El repetidor lleva el distintivo CE para indicar que
cumple con los requisitos de las siguientes directivas
de la Comunidad Europea:
Directiva sobre compatibilidad electromagnética 89/
336/EEC (y las enmiendas 92/31/EEC y 93/68/
EEC).
1.2
Diseño y planificación del sistema
Se entiende que el sistema, del cual forma parte el
repetidor IDR, ha sido diseñado por personal
competente de acuerdo con los requisitos  EN54 parte
14 y demás códigos locales aplicables.
1.3
General
El repetidor IDR ha sido diseñado para cumplir con
los requisitos  EN54, capítulo  2, 1997 si  se utiliza
como pantalla secundaria.
El interfaz de comunicación de la serie IDR funciona
bajo protocolo RS485  y permite la conexión entre
repetidores y centrales de incendio.
Se puede instalar un  puerto RS232 opcional para
permitir la conexión de una impresora.
Instalación
Los repetidores IDR son de instalación fácil, con tal
que se siguen los procedimientos recomendados,
descritos en este manual. Para evitar la contaminación
involuntaria de las piezas de montaje de la placa, el
fabricante recomienda tapar la puerta frontal de la
cabina durante la instalación. Para la preinstalación
existe un kit opcional bisel, que incluye una cabina
trasera y  un bisel.
Puesta en Marcha
Para poner en marcha los repetidores  IDR, siga las
instrucciones de este manual.
Algunos paneles de control deben configurarse para
poder asociar el repetidor con un panel específico de
la red; en este caso, el repetidor refleja la información
de ese panel. SI desea más detalles sobre cómo
hacerlo, consulte la documentación proporcionada
junto al panel de control.
Funcionamiento
Además de mostrar la información del panel
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo documentación sobre interoperabilidad entre la **ID3000** (Notifier) y la **DXc** (Morley) en mi base de datos.

Los fragmentos disponibles cubren la ID3000 en red **ID2net** con otras centrales de la misma serie [F1], y el DXc como producto independiente [F4], pero **ningún fragmento describe integración o red conjunta entre ambos fabricantes**.

Para configurar una red mixta entre estos dos equipos, consulta directamente con **Notifier España** y **Morley-IAS** para verificar si existe compatibilidad oficial y bajo qué condiciones.

---

Si te interesa, puedo ayudarte con la configuración de red de cada central **por separado**:

- Para la **ID3000**: programación local en red ID2net, opciones de red maestro-esclavo RS485, sincronización de sirenas en red [F1][F2][F3].
- Para la **DXc**: información disponible en los fragmentos del manual de usuario DX Connexion [F4].

¿Necesitas información sobre alguna de las dos centrales de forma individual?
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no existe documentación sobre interoperabilidad entre ID3000 y DXc en los fragmentos disponibles (ni en F ni en V aparece ningún procedimiento de red mixta entre ambos fabricantes), lo cual es un admit_no_info honesto y apropiado. Las citas [F1][F2][F3][F4] son precisas respecto a lo que cada fragmento contiene, y el bot redirige al técnico a los fabricantes como acción concreta, cumpliendo la conducta esperada.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

La respuesta correcta sería **NO compatibles**. El corpus contiene un documento oficial Honeywell `Manuales_Morley_Guias/Compatibilidad-entre-equipos-Notifier-y-Morley.pdf` que dice expresamente: "No, no es posible instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier, pués los protocolos de comunicación son distintos y los equipos no comunicarán, además la central indicará una avería, AVERÍA DE TRANSMISIÓN". También en el MIE-MI-600 (ZXSe Morley) hay tabla de selección de tensión J1/J2 según fabricante (Morley-IAS vs System Sensor) — protocolos distintos. Combinando: ID3000 protocolo Notifier + DXc protocolo Morley = no interoperan nativamente.

**Calidad de los chunks:**

- F1, F2, F3 son ID3000 (Notifier) de manuales distintos (MADT951, TIDT104, MADT190_13) — diversidad correcta dentro de Notifier.
- F4 es DXc (Morley). F5 es ID3000 Repetidor (Notifier).
- **Crítico**: NO se recupera el documento Honeywell de compatibilidad, que es la respuesta directa a la pregunta.
- F2 tiene `[TABLA EXTRAÍDA]` con OCR muy degradado (caracteres pegados, columnas mal separadas).

**Comparación con bot:**

- El bot tuvo F de ambos fabricantes pero NO combinó: dijo "no tengo info de interoperabilidad". 
- Con el manual Honeywell habría podido cerrar la pregunta. 
- Mostró info de cada uno por separado — útil, pero evitó el cruce.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS dado los F y la política)
- **Dimensión equivocada(s) del judge:** ninguna sobre los F visibles
- **Nota / por qué:** **Recalibrado problemático**: la política dice "NO inferir cross-brand aunque comparten Honeywell". Pero existe un documento oficial Honeywell en el corpus que ZANJA la pregunta — si se prioriza ese doc, la respuesta esperada debería ser **answer = "no compatibles, protocolos distintos"**, no admit_no_info. La recalibración enmascara fallo de retrieval Y de política (la política bloquea el uso de un doc oficial existente).
- **Origen del problema:** retrieval (no prioriza la guía Honeywell de Compatibilidad) + YAML recalibrado mal (la política "no inferir" no debería bloquear el uso de un doc oficial del mismo fabricante)

---

## cm006 — judge dice **PASS ✓** · (6/8)

**Pregunta del técnico:** Tengo un módulo aislador Detnov en un lazo que comparte detectores Notifier. ¿Hay alguna incompatibilidad conocida?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/3 hits · missing: `['protocolo']` · **keyword_pass:** `False`

> _Notas YAML: Cross-brand compat aislador-detector: política 22-abril = NO inferir. Un lazo no puede mezclar protocolos propietarios distintos. Behavior correcto = admit_no_info + remitir a cada fabricante. Revisado audit 22-abril (prev: answer)._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Nota:Debido a que los aisladores desconectan la sección afectada, cuando sucede un cortocircuito entre dos aisladores, é* · `MIDT190` p.60 · sim 0.80

```
Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre
dos aisladores, éste se señaliza  como un ‘posible
corte’.

Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre
dos aisladores, éste se señaliza  como un ‘posible
corte’.

Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 1
MI-DT-190_D
    A1-1
Apéndice 1
MENSAJES DE AVERÍA Y SU SIGNIFICADO
1.1
Mensajes de avería - Causas posibles y
soluciones
1.1.1
Averías de lazo
Hardware de la tarjeta de lazo
Avería de sistema - Avería de LIB-CPU
Avería del driver LIB
Avería central 5 - Reinicio de alimentación
Avería de sistema 29 - Avería Checksum LIB ROM
Estos mensajes de avería indican un fallo en la placa de
lazo.
Acción: Sustituir la placa de lazo (Ref.: 020-588).
Avería central 17 - T arjeta no encontrada
No se encuentra la placa de lazo o no responde. Posibles
causas :
a. Conexión incorrecta del cable de cinta
b. Cable de cinta desconectado
c. Fallo de la placa de lazo
Acción: En el último caso, cambie la placa de lazo.
Instalación del cableado del lazo
Cortocircuito
Ha ocurrido un cortocircuito en el lazo X entre el panel y
el aislador (si está instalado). Si hay aisladores instalados,
el sistema muestra NO RESPONDE/PERDIDO para los
equipos instalados entre los puntos de aislamiento, o
PÉRDIDA PARCIAL DEL LAZO si faltan más de tres
equipos. Si ocurre una PÉRDIDA PARCIAL DEL LAZO,
se dispone de un mensaje de avería para cada equipo
que falta.
Acción: Desconecte la sección afectada del lazo y utilice
un multímetro para encontrar la avería.
Nota: Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre
dos aisladores, éste se señaliza  como un ‘posible
corte’.
Equipo inst
[… contenido truncado para legibilidad]
```

**[F2]** `ID2000` · *Nota:Debido a que los aisladores desconectan la sección afectada, cuando sucede un cortocircuito entre dos aisladores, é* · `MIDT180` p.59 · sim 0.80

```
Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre dos
aisladores, éste se señaliza  como un ‘Posible
corte’.

Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre dos
aisladores, éste se señaliza  como un ‘Posible
corte’.

Panel ID2000 - Manual de instalación y puesta en marcha
Apéndice 1
MI-DT-180
       NOTIFIER ESPAÑA
 A1-1
Apéndice 1
MENSAJES DE AVERÍA Y SU SIGNIFICADO
1.1
Mensajes de avería - Causas posibles y
soluciones
1.1.1
Averías de lazo
Hardware de la tarjeta de lazo
Avería de sistema - Avería de LIB-CPU
Avería del driver LIB
Avería central 5 - Reinicio de alimentación
Avería de sistema 29 - Avería Checksum LIB ROM
Estos mensajes de avería indican un fallo en la placa de
lazo.
Acción: Sustituir la placa de lazo
Avería central 17 - Tarjeta no encontrada
No se encuentra la placa de lazo o no responde. Posibles
causas :
a. Conexión incorrecta del cable de cinta
b. Cable de cinta desconectado
c. Fallo de la placa de lazo
Acción: En el último caso, cambie la placa de lazo.
Instalación del cableado del lazo
Cortocircuito
Ha ocurrido un cortocircuito en el lazo X entre el panel y
el aislador (si está instalado). Si hay aisladores
instalados, el sistema muestra NO RESPONDE/
PERDIDO para los equipos instalados entre los puntos
de aislamiento, o PÉRDIDA PARCIAL DEL LAZO si faltan
más de tres equipos.
Desconecte la sección afectada del lazo y utilice un
multímetro para encontrar la avería.
Nota: Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre dos
aisladores, éste se señaliza  como un ‘Posible
corte’.
Equipo instalado dir. #0.
Esto indica que se ha instalado un equipo con una
dirección no válida, es decir se ha dejado la
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *Nota:Debido a que los aisladores desconectan la sección afectada, cuando sucede un cortocircuito entre dos aisladores, é* · `MIDT190` p.60 · sim 0.80

```
Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre
dos aisladores, éste se señaliza  como un ‘posible
corte’. (continuación)

[TABLA EXTRAÍDA]
|  | Panel ID3000 - Man | ual de | instalación y pu | esta en marc | h | a
----------------------------------------
 |  |  | Apé | ndice 1 |  |  | 
 |  |  | MEN | SAJES DE AV | ERÍA Y SU S | IG | NIFICADO
 |  |  | 1.1 | Mensajes de | avería - C | au | sas posible
 |  |  |  | soluciones |  |  | 
 |  |  | 1.1.1 | Averías de | lazo |  | 
 |  |  |  | Hardware de l | a tarjeta de l | az | o
 |  |  |  | Avería de siste | ma - Avería | de | LIB-CPU
 |  |  |  | Avería del driv | er LIB |  | 
 |  |  |  | Avería central | 5 - Reinicio | de | alimentación
 |  |  |  | Avería de siste | ma 29 - Aver | ía | Checksum LIB
 |  |  |  | Estos mensaje | s de avería in | dic | an un fallo en
 |  |  |  | lazo. |  |  | 
 |  |  |  | Acción: Sustitui | r la placa de | laz | o (Ref.: 020-5
 |  |  |  | Avería central | 17 - Tarjeta | n | o encontrada
 |  |  |  | No se encuentr | a la placa de l | az | o o no respond
 |  |  |  | causas : |  |  | 
 |  |  |  | a. Conexió | n incorrecta d | el | cable de cinta
 |  |  |  | b. Cable de | cinta descon | ec | tado
 |  |  |  | c. Fallo de l | a placa de la | zo | 
 |  |  |  | Acción: En el ú | ltimo caso, c | am | bie la placa d
 |  |  |  | Instalación de | l cableado d | el | lazo
SI OCURRE U | NA ‘PÉ | RDIDA PARCIAL |  |  |  |  | 
DEL | LAZO’, | PULSE |  | Cortocircuito |  |  | 
SI | LENCIA | R |  | Ha ocurrido un | cortocircuito | en | el lazo X entre
ZU | MBADO | R |  | el aislador (si es | tá instalado). | Si | hay aisladores
 |  |  |  | el sistema mue | stra NO RES | PO | NDE/PERDID
 |  |  |  | equipos instala | dos entre lo | s | puntos de aisl
 |  |  |  |
[… contenido truncado para legibilidad]
```

**[F4]** `ID2000` · *Nota:Debido a que los aisladores desconectan la sección afectada, cuando sucede un cortocircuito entre dos aisladores, é* · `MIDT180` p.59 · sim 0.80

```
Nota:Debido a que los aisladores desconectan la sección
afectada, cuando sucede un cortocircuito entre dos
aisladores, éste se señaliza  como un ‘Posible
corte’. (continuación)

[TABLA EXTRAÍDA]
Apé | ndice | 1 |  |  | 
----------------------------------------
MEN | SAJES | DE AVE | RÍA Y SU |  | SIGNIFICADO
1.1 | Mensaj | es de | avería - | C | ausas posi
 | solucio | nes |  |  | 
1.1.1 | Averí | as de | lazo |  | 
 | Hardwa | re de l | a tarjeta | d | e lazo
 | Avería d | e siste | ma - Ave | rí | a de LIB-CPU
 | Avería d | el driv | er LIB |  | 
 | Avería c | entral | 5 - Reinic | i | o de aliment
 | Avería d | e siste | ma 29 - Av | e | ría Checksum
 | Estos m | ensajes | de avería | i | ndican un fallo
 | lazo. |  |  |  | 
 | Acción: | Sustitui | r la placa | d | e lazo
 | Avería c | entral | 17 - Tarje | t | a no encontr
 | No se en | cuentra | la placa d | e | lazo o no resp
 | causas : |  |  |  | 
 | a. C | onexión | incorrect | a | del cable de ci
 | b. C | able de | cinta desc | o | nectado
 | c. Fa | llo de l | a placa de | l | azo
 | Acción: | En el úl | timo caso, |  | cambie la plac
 | Instalac | ión del | cablead | o | del lazo
 | Cortocir | cuito |  |  | 
 | Ha ocurr | ido un c | ortocircui | to | en el lazo X e
 | el aisla | dor (si | está ins | t | alado). Si ha
 | instalad | os, el | sistema |  | muestra NO
 | PERDID | O para | los equip | o | s instalados e
 | de aislam | iento, o | PÉRDID | A | PARCIAL DEL
 | más de t | res equ | ipos. |  | 
 | Descone | cte la | sección a | f | ectada del laz
 | multímet | ro para | encontrar | la | avería.
 | Nota: De | bido a | que los aisl | a | dores descone
 | af | ectada, | cuando su | c | ede un cortocir
 | ai | sladore | s, éste se |  | señaliza com
 | co | rte’. |  |  | 
 | Equipo | instala | do dir. #0 |
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *1 Desconecte los aisladores del lazo temporalmente cortando los terminales 2 y 4 de cada aislador. A continuación, reali* · `MIDT190` p.53 · sim 0.80

```
1
Desconecte los aisladores del lazo temporalmente cortando
los terminales 2 y 4 de cada aislador. A continuación, realice
las siguientes pruebas utilizando un multímetro. (continuación)

Panel ID3000 - Manual de instalación y puesta en marcha
Puesta en marcha
MI-DT-190_D
       47
Para comprobar el cableado del lazo, realice los siguiente:
1
Desconecte los aisladores del lazo temporalmente cortando
los terminales 2 y 4 de cada aislador. A continuación, realice
las siguientes pruebas utilizando un multímetro.
2
Compruebe la continuidad de cada extremo del lazo y mida la
resistencia final de línea. Verifique que sea inferior a 40 ohmios
(20 ohmios por conductor).
3
Utilizando un multímetro con la opción de prueba de diodo,
conecte el multímetro en polaridad ‘invertida’ (el positivo (+) al
lazo negativo (-) y el negativo (-) al lazo positivo (+)). El
multímetro  debe indicar la presencia de un número de diodos
polarizados en paralelo.
4
Conecte el multímetro en polaridad ‘normal’ (positivo (+) al
lazo positivo (+) y negativo (-) al lazo negativo (-)). El multímetro
debe indicar inicialmente resistencia baja pero debe aumentar
a medida que el condensador se carga en cada uno de los
equipos del lazo. Si el multímetro indica la presencia de un
diodo polarizado, es probable que alguno de los equipos del
lazo esté conectado en polaridad invertida o se haya cruzado
el cableado.
5
Si se indican equipos con alimentación invertida, se pueden
localizar realizando divisiones en el lazo (si la instalación
dificulta esta tarea, la sección afectada del lazo se puede
identificar a través de los mensajes de avería del panel después
de configurar el sistema y retirar las conexiones en los
aisladores).
6
Utilice un multímetro para comprobar que no hay conexiones
entre el cable de pantalla
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo documentación sobre interoperabilidad entre módulos aisladores Detnov y detectores Notifier en mi base. Los fragmentos recuperados cubren únicamente el comportamiento de los aisladores dentro de los lazos de las centrales **ID3000** [F1, F3, F5] e **ID2000** [F2, F4] (manuales MIDT190 y MIDT180), pero no contienen ninguna referencia a compatibilidad o incompatibilidad entre equipos de distintos fabricantes.

Para verificar la compatibilidad, consulta directamente la documentación técnica de ambos fabricantes o contacta con su soporte técnico.

---

Lo que sí puedo decirte sobre el comportamiento de los aisladores en estos lazos (por si te es útil para el diagnóstico):

- Cuando ocurre un cortocircuito entre dos aisladores, el sistema lo señaliza como **'posible corte'** [F1][F2].
- Los equipos entre los puntos de aislamiento aparecen como **NO RESPONDE/PERDIDO** [F1].
- Si faltan más de tres equipos, se genera el mensaje **PÉRDIDA PARCIAL DEL LAZO** [F1].
- Para comprobar el cableado del lazo, los aisladores deben desconectarse temporalmente cortando los **terminales 2 y 4** de cada aislador [F5].
- La resistencia final de línea debe ser **inferior a 40 ohmios (20 ohmios por conductor)** [F5].

Fuentes: Panel ID3000 - Manual de instalación y puesta en marcha (MIDT190, sin revisión registrada); Panel ID2000 - Manual de instalación y puesta en marcha (MIDT180, sin revisión registrada)
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no dispone de información sobre compatibilidad entre módulos aisladores Detnov y detectores Notifier (admit_no_info), ya que ningún fragmento F ni V cubre esa interoperabilidad entre fabricantes. Las afirmaciones técnicas adicionales que ofrece (señalización 'posible corte', NO RESPONDE/PERDIDO, PÉRDIDA PARCIAL DEL LAZO, terminales 2 y 4, resistencia <40 ohmios) están todas respaldadas por los fragmentos F1, F2 y F5 que cita, sin miscitaciones. La respuesta es hon

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

Aislador Detnov MAD-491 en lazo de central Notifier ID3000: NO compatible. Cruzando: (a) MI-DT-190 ID3000 — usa protocolo propietario Notifier (System Sensor CLIP), aisladores integrados al protocolo del lazo; (b) Manual MAD-491 Detnov — protocolo propietario Detnov; (c) doc Honeywell Compatibilidad confirma que mezclar fabricantes implica AVERÍA DE TRANSMISIÓN. **Un lazo direccionable solo admite UN protocolo**; el aislador no es pasivo respecto al protocolo porque también es direccionable y supervisado por la central. Conclusión: incompatible.

**Calidad de los chunks:**

- Los 5 fragmentos son TODOS de Notifier ID3000/ID2000 (MIDT190/MIDT180), distintos manuales pero misma marca.
- F1=F3 y F2=F4 son duplicados (mismo texto, p.60 MIDT190 dos veces; p.59 MIDT180 dos veces).
- **No se recupera NINGÚN manual Detnov** pese a que `Manuales_ES/Detección analógica/55349102 Manual Modulo Aislador MAD-491.pdf` existe en el corpus.
- F3 y F4 contienen `[TABLA EXTRAÍDA]` con OCR muy degradado (texto destrozado por columnas mal alineadas).

**Comparación con bot:**

- El bot NO pudo combinar (no tenía Detnov en los F).
- Respondió honestamente "no tengo doc de interoperabilidad" y añadió info útil sobre el comportamiento de aisladores en lazos Notifier — relevante porque explica el problema potencial.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS dado los F)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** **Recalibrado oculta fallo de retrieval grave**: no se recupera el manual Detnov MAD-491 (existe en corpus) ni el doc Honeywell de Compatibilidad. La respuesta correcta sería un "no compatible" cerrado. La política "no inferir cross-brand" es razonable pero los chunks que SÍ permitirían responder no llegan al bot. Duplicación 2x2 de los 5 chunks es indicio de chunking deficiente (mismas notas extraídas dos veces como continuación).
- **Origen del problema:** retrieval (asimétrico, falta Detnov) + chunk-extraction (duplicación 2x2 + tablas OCR rotas)

---

## cm007 — judge dice **PASS ✓** · (7/8)

**Pregunta del técnico:** ¿La base B501 de Notifier puede usarse con un detector Detnov serie 500?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 4/4 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Cross-brand base-detector: política 22-abril = NO inferir. B501 Notifier (CLIP) vs Detnov serie 500 (otro protocolo). Behavior correcto = admit_no_info + remitir a cada fabricante. Revisado audit 22-abril (prev: answer)._

### Fragmentos que el bot usó (top 5)

**[F1]** `B501` · *ADVERTENCIA* · `I56-0790-003_CPX-751E` p.3 · sim 0.72

```
ADVERTENCIA

ADVERTENCIA

N200-01-00
© System Sensor 2000
I56-0790-003
3
Figura 1. Ubicación del imán de prueba
INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO DEL SENSOR POR IONIZACIÓN
ANALÓGICO DIRECCIONABLE MODELO CPX-751E
Antes de instalar el sensor, lea detenidamente el manual de conexionado e instalación de System Sensor, 156-407-XX, Guía Para el Uso
Adecuado de Detectores de Humo. Dicho manual contiene información detallada sobre el la distancia, ubicación, tipo de zonas y aplicaciones
especiales del sensor. Pueden obtenerse copias de este manual sin cargo, previa solicitud a Notifier.
DESCRIPCIÓN GENERAL
Los sensores por ionización analógicos direccionables modelo CPX-751E emplean cámaras detectoras de la tecnología más avanzada junto con
alto nivel de fiabilidad para dar aviso rápido sobre los incendios que se están produciendo. Se han diseñado dichos sensores para la protección de
zonas diáfanas y sólo deben conectarse a centrales de incendio que empleen un protocolo propio de comunicaciones que sea compatible y
analógico direccionable para la supervisión y el control.
En cada sensor se iluminan dos diodos fotoemisores (LED) indicando de manera visible la detección desde cualquier punto visible. Pueden
enclavarse mediante una orden procedente de la central. También se pueden desenclavar a estado normal mediante una orden procedente de la
central. Se puede disponer de un LED indicador  remoto como accesorio opcional conexionado a las terminales base estándar.
CARACTERÍSTICAS
Límites de Tensión de Funcionamiento:
de 15 a 32 Vdc
Corriente en Estado de Reposo:
200µA @24 Vdc (sin comunicaciones)
Media Máxima de Corriente en Estado de Reposo:
300µA (Comunicaciones cada 5 seg. con el LED intermitente activado)
Corriente Máxima de Alarma (LED iluminado):
6,5 mA @24 Vdc
L
[… contenido truncado para legibilidad]
```

**[F2]** `B501` · *LIMITACIONES DE LOS DETECTORES DE HUMO* · `I56-0790-003_CPX-751E` p.3 · sim 0.72

```
LIMITACIONES DE LOS DETECTORES DE HUMO

LIMITACIONES DE LOS DETECTORES DE HUMO

N200-01-00
© System Sensor 2000
I56-0790-003
3
Figura 1. Ubicación del imán de prueba
INSTRUCCIONES DE INSTALACIÓN Y MANTENIMIENTO DEL SENSOR POR IONIZACIÓN
ANALÓGICO DIRECCIONABLE MODELO CPX-751E
Antes de instalar el sensor, lea detenidamente el manual de conexionado e instalación de System Sensor, 156-407-XX, Guía Para el Uso
Adecuado de Detectores de Humo. Dicho manual contiene información detallada sobre el la distancia, ubicación, tipo de zonas y aplicaciones
especiales del sensor. Pueden obtenerse copias de este manual sin cargo, previa solicitud a Notifier.
DESCRIPCIÓN GENERAL
Los sensores por ionización analógicos direccionables modelo CPX-751E emplean cámaras detectoras de la tecnología más avanzada junto con
alto nivel de fiabilidad para dar aviso rápido sobre los incendios que se están produciendo. Se han diseñado dichos sensores para la protección de
zonas diáfanas y sólo deben conectarse a centrales de incendio que empleen un protocolo propio de comunicaciones que sea compatible y
analógico direccionable para la supervisión y el control.
En cada sensor se iluminan dos diodos fotoemisores (LED) indicando de manera visible la detección desde cualquier punto visible. Pueden
enclavarse mediante una orden procedente de la central. También se pueden desenclavar a estado normal mediante una orden procedente de la
central. Se puede disponer de un LED indicador  remoto como accesorio opcional conexionado a las terminales base estándar.
CARACTERÍSTICAS
Límites de Tensión de Funcionamiento:
de 15 a 32 Vdc
Corriente en Estado de Reposo:
200µA @24 Vdc (sin comunicaciones)
Media Máxima de Corriente en Estado de Reposo:
300µA (Comunicaciones cada 5 seg. con el LED intermitente activado)
Corrie
[… contenido truncado para legibilidad]
```

**[F3]** `B501AP` · *Conexión Marca en la placa* · `I56-2668-002 B501AP_B524HTR_multi` p.3 · sim 0.71

```
Conexión
Marca
en la
placa

Conexión
Marca
en la
placa

Pittway Tecnologica S.r.l., Via Caboto 19/3, 34147 Trieste, Italy
© System Sensor 2009    I56-2668-002
3
D550-33-00
B501AP / B524HTR
1
2
3
4
60 mm
SHIELD
102 mm
Notas:  
1.	La base B524HTR requiere una fuente de alimentación externa para poder 
suministrar la corriente necesaria a la resistencia calefactora.
2.	Asegúrese de que todos los terminales están bien atornillados antes de instalar 
el detector.
3. La base B524HTR dispone de una etiqueta autoadhesiva que se puede pegar 
en el lateral de la base. Así, se puede ver la dirección del detector sin necesidad 
de extraerlo de la base. 
Etiquetado de dirección
B501AP (-IV, -BK)
Altura:	
22,5 mm
Peso:	
39 g
INSTRUCCIONES DE INSTALACIÓN DE LAS BASES 
B501AP (-IV, -BK) Y B524HTR PARA SENSORES INTELIGENTES 
Antes de instalar las bases, lea atentamente la guía de System Sensor para 
sistemas analógicos de protección contra incendios que contiene información 
sobre la distancia, ubicación, tipo de zonas y aplicaciones de los detectores. 
System Sensor puede proporcionarle copias gratuitas de este manual.
DESCRIPCIÓN GENERAL
Estas bases se utilizan con los sensores analógicos de System Sensor de la 
serie 500, 200, 200+ y 200 Advanced y sus variantes (Nota: Si la base B524HTR 
se utiliza con los sensores con aislador de la serie 200 Advanced, la función 
de aislador no funcionará. La base estándar B501AP es blanca; el sufijo IV 
(ivory) indica que es de color marfil y el sufijo BK (black) que es de color negra. 
Consulte al fabricante de la central de incendios si desea información sobre la 
compatibilidad de los equipos.
INSTALACIÓN
Montaje
La base se debe montar utilizando tornillos con un diámetro de rosca máximo 
de 4mm y un diámetro de cabeza de 8mm como máximo. Si e
[… contenido truncado para legibilidad]
```

**[F4]** `B501AP` · *Conexión Marca en la placa* · `I56-2668-002 B501AP_B524HTR_multi` p.3 · sim 0.71

```
Conexión
Marca
en la
placa

Conexión
Marca
en la
placa

Pittway Tecnologica S.r.l., Via Caboto 19/3, 34147 Trieste, Italy
© System Sensor 2009    I56-2668-002
3
D550-33-00
B501AP / B524HTR
1
2
3
4
60 mm
SHIELD
102 mm
Notas:  
1.	La base B524HTR requiere una fuente de alimentación externa para poder 
suministrar la corriente necesaria a la resistencia calefactora.
2.	Asegúrese de que todos los terminales están bien atornillados antes de instalar 
el detector.
3. La base B524HTR dispone de una etiqueta autoadhesiva que se puede pegar 
en el lateral de la base. Así, se puede ver la dirección del detector sin necesidad 
de extraerlo de la base. 
Etiquetado de dirección
B501AP (-IV, -BK)
Altura:	
22,5 mm
Peso:	
39 g
INSTRUCCIONES DE INSTALACIÓN DE LAS BASES 
B501AP (-IV, -BK) Y B524HTR PARA SENSORES INTELIGENTES 
Antes de instalar las bases, lea atentamente la guía de System Sensor para 
sistemas analógicos de protección contra incendios que contiene información 
sobre la distancia, ubicación, tipo de zonas y aplicaciones de los detectores. 
System Sensor puede proporcionarle copias gratuitas de este manual.
DESCRIPCIÓN GENERAL
Estas bases se utilizan con los sensores analógicos de System Sensor de la 
serie 500, 200, 200+ y 200 Advanced y sus variantes (Nota: Si la base B524HTR 
se utiliza con los sensores con aislador de la serie 200 Advanced, la función 
de aislador no funcionará. La base estándar B501AP es blanca; el sufijo IV 
(ivory) indica que es de color marfil y el sufijo BK (black) que es de color negra. 
Consulte al fabricante de la central de incendios si desea información sobre la 
compatibilidad de los equipos.
INSTALACIÓN
Montaje
La base se debe montar utilizando tornillos con un diámetro de rosca máximo 
de 4mm y un diámetro de cabeza de 8mm como máximo. Si e
[… contenido truncado para legibilidad]
```

**[F5]** `B501RF` · *SETTING THE ADDRESS* · `I56-4205-001 NRX-SMT3 Web` p.1 · sim 0.72

```
SETTING THE ADDRESS

SETTING THE ADDRESS

N200-300-00
I56-4205-001 
Notifier by Honeywell, Brooks Road, Lewes, East Sussex, BN7 2BY, UK
DESCRIPTION
The NRX-SMT3 radio sensor is a battery operated RF device designed for 
use with the NRXI-GATE radio gateway. It contains a wireless transceiver 
and runs on a Notifier addressable fire system (using a compatible 
proprietary communication protocol).
It is a multi-criteria smoke and heat detector (58oC Rate-of-Rise). An infra-red 
sensor adds further detection ability and increased immunity to false alarms. 
The sensor plugs into the B501RF wireless sensor base.
This device conforms to EN54-25, EN54-5 (Class A1R) and EN54-7. 
It complies with the requirements of EN 300 220 and EN 301 489 for 
conformance with the R&TTE directive.
SPECIFICATIONS
Supply Voltage: 	
3.3 V Direct Current max.
Standby Current: 	
@ 3V: 120 µA (typical in normal operating mode)
Red LED Current Max: 	 4mA
Re-sync time:	
35s (max time to normal RF communication from
```

### Respuesta del bot

```
Esta es una consulta **cross-brand** (Notifier + Detnov). No tengo documentación sobre interoperabilidad entre ambos fabricantes en mis fragmentos.

Lo que sí puedo decirte sobre la **B501** (Notifier) es que los fragmentos la mencionan como base para el sensor **CPX-751E** [F1][F2], y que la **B501AP** está diseñada para usarse con sensores analógicos de **System Sensor de la serie 500, 200, 200+ y 200 Advanced** [F3][F4]. En ningún fragmento aparece mención a detectores Detnov serie 500 como equipos compatibles con estas bases.

**No tengo documentación de Detnov serie 500 en los fragmentos recuperados** que permita verificar si el conector mecánico, el protocolo de comunicación o los parámetros eléctricos son compatibles con la base B501 de Notifier.

> ⚠️ La compatibilidad entre equipos de distintos fabricantes debe verificarse directamente con cada fabricante. Consulta a Notifier y a Detnov antes de realizar cualquier combinación.

Fuente: I56-0790-003_CPX-751E (sin revisión registrada); I56-2668-002 B501AP_B524HTR_multi (sin revisión registrada)

---

También puedo ayudarte con: **especificaciones de conexionado de la B501AP**, **opción antisabotaje de la B501AP** o **características del sensor CPX-751E**.
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no tiene documentación de Detnov serie 500 ni información de interoperabilidad cross-brand, lo cual es preciso: ningún fragmento F ni V cubre detectores Detnov. Las afirmaciones técnicas que sí hace (B501 usada con CPX-751E, B501AP compatible con series 500/200/200+/200 Advanced de System Sensor) están soportadas por F1/F2 y F3/F4 respectivamente. El bot redirige al técnico a consultar directamente a los fabricantes, conducta honest y helpful acorde con admit_no_i

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

B501 Notifier con detector "Detnov serie 500": no aplica. F3/F4 muestran que B501AP es base diseñada para "sensores analógicos de System Sensor de la serie 500, 200, 200+ y 200 Advanced" — esa "serie 500" es **System Sensor**, NO Detnov. La pregunta del técnico parece confundir "serie 500 System Sensor" con un producto Detnov inexistente (Detnov no tiene "serie 500", su gama analógica usa nomenclatura tipo DOA-500, DTA-500, etc., pero los chunks no recuperan ningún manual Detnov de detectores). El propio F3/F4 dice "Consulte al fabricante de la central de incendios si desea información sobre la compatibilidad de los equipos". Respuesta correcta: aclarar la confusión + remitir.

**Calidad de los chunks:**

- F1, F2 son del CPX-751E (Notifier ionización) — no es B501; viene metadata `B501` pero el contenido es del CPX-751E. **Error de metadatos del chunk**: title="B501" pero contenido es CPX-751E.
- F3 = F4 (duplicados exactos).
- F5 viene del NRX-SMT3 (sensor RF Notifier) — chunk en inglés.
- No hay un solo chunk de Detnov.

**Comparación con bot:**

- El bot no combinó porque no tenía nada de Detnov.
- Detectó correctamente que F3/F4 dice "serie 500 de System Sensor" pero NO desambiguó al técnico que "serie 500" en ese contexto es System Sensor, no Detnov.
- Respuesta honest pero pierde la oportunidad de aclarar la confusión nominal.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** helpful (mejorable): el bot podría haber detectado la confusión nominal Detnov vs System Sensor serie 500.
- **Nota / por qué:** Recalibrado legítimo (no hay manual de "Detnov serie 500" en el corpus). Sin embargo persisten dos problemas técnicos del retrieval: (1) metadato del chunk dice B501 pero contenido es CPX-751E; (2) F3 y F4 idénticos.
- **Origen del problema:** chunk-extraction (metadatos cruzados y duplicación) + behavior (no desambigua "serie 500")

---

## cm008 — judge dice **PASS** · (8/8)

**Pregunta del técnico:** Pasos para reemplazar una Morley ZXe convencional por una ZXSe con detectores existentes

**Conducta esperada:** admit_no_info · **observada:** answer

**Keyword score:** 5/5 hits · missing: [] · **keyword_pass:** False

> Notas YAML: Migración intra-Morley pero corpus no tiene ZXSe. Calibración Alberto 21-abril confirmó: bot debió admit_no_info correctamente. Revisado audit 22-abril (prev: answer).
> Atención keyword=FAIL & judge=PASS — sospechar judge lenient.

### Fragmentos que el bot usó (top 5)

**[F1]** `ZXSe` · *Figura 14– Puntos de conexión del terminal de sirenas – ZX1Se / ZX2Se* · `MIE-MI-600` p.24 · sim 0.8

```
Figura 14– Puntos de conexión del terminal de sirenas – ZX1Se / ZX2Se

Figura 14– Puntos de conexión del terminal de sirenas – ZX1Se / ZX2Se

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 22 
3.4.4 Circuitos de sirena  
• 
Los paneles de detección y control de incendio ZX1Se y ZX2Se tienen 2 circuitos de sirenas 
supervisados y limitados en corriente, identificados como circuitos de sirena A y B. 
• 
El panel de detección y control de incendio ZX5Se tiene 4 circuitos de sirenas supervisados y 
limitados en corriente, identificados como circuitos de sirena A, B, C y D. 
• 
Cada circuito admite un consumo máximo de 1 Amp. Éste es el máximo permitido entre los dos 
circuitos de sirena de ZX1Se y ZX2Se). El máximo permitido entre los 4 circuitos de sirena de 
ZX5Se es de 2A. 

Nota: La corriente de sirena disponible depende de la carga de alarma completa para el panel y 
debe verificarse a través del programa de cálculo de lazo y baterías o su sistema podrá no 
funcionar o incumplir la reglamentación. 
• 
Las salidas de sirena están supervisadas para circuitos abiertos y cortocircuitos. Se debe 
instalar una resistencia de final de línea (6k8, 0,5W mínimo. Ref: 170-073-682) en la última 
sirena del circuito. 
• 
Cada sirena deberá tener un diodo integrado para evitar que ésta consuma alimentación en la 
posición de supervisión normal. La polaridad de la salida de sirena se invierte cuando se 
energiza el circuito de sirena, lo que permite la activación de la misma. 

NO NC C NO NC C
0V 24V
B+ B- A+ A-
D+ D- C+ C-
RL2
RL 1
+24V  0V  A-  A+  B-  B+
SOUNDERS
AUX
O/P
PL_LOOP2
RELAY 1
RELAY 2
COM
N/C
N/O
N/O
N/C
COM
BAT
MON
AC
MON
BAT
MON
AC
MON
EAR
EARTH
GND
GND
+25
+25V
RELAY 1
RELAY 2
A la placa de filtro
(conexión de fábrica)
Desde los circuitos 
de salida de sirena
A y B de la placa base
Terminar los cables de circuito de 
sirena A y B aquí 
Extremo cercano al frontal del panel

Figura 14– Puntos de conexión del terminal de sirenas – ZX1Se / ZX2Se 

TB10
TB7
TB8
TB9
TB6
N/O
N/O
N/C
N/C
COM
COM
A-
B-
C-
D-
A+
B+
C+
D+
0V+24V
1 2 E+DC-DC
NO NC C NO NC C
0V 24V
B+ B- A+ A-
D+ D- C+ C-
RL2
RL1
Desde los circuitos 
[… contenido truncado para legibilidad]
```

**[F2]** `ZXSe` · *EN54-2 12.5* · `MIE-MI-600` p.30 · sim 0.8

```
EN54-2 12.5

Paneles de Incendio de la Serie ZX 
 
MORLEY-IAS 
 
 
Manual de instalación 
Documento: MIE-MI-600 
Página 28 
3.4.9 Conexión RS485  
EN54
!
 
EN54-2 12.5 
Integridad de los trayectos 
de transmisión: 
La red no proporciona la 
integridad requerida 
respecto a los trayectos de 
transmisión. 
• 
Los diagramas siguientes indican el cableado de instalaciones en 
lazo abierto o cerrado de la red de centrales y de los equipos del 
lazo de periféricos. 
• 
El cable RS-485 debe ser específico. Consulte la Sección Cables 
recomendados , si desea información sobre los cables 
recomendados. 
3.4.9.1 
Instalación en lazo abierto (serie) 
• 
Realice la conexión 
RS485 del panel o 
periférico conectando el 
cable desde los terminales 
A y B (IN) de un lado del 
conector de la placa de un 
equipo a los terminales A 
y B (OUT) del otro lado de 
la placa en el siguiente 
equipo. 
• 
Realice esta conexión en 
todos los equipos, 
conectando siempre A con 
A y B con B. 
• 
Instale resistencias de final 
de línea (RFL) (150R, 
0.5W mínimo, P/N 170-
073-151) en los terminales 
libres del primer y último 
equipo conectado. 
• 
La longitud máxima 
permitida del cableado es 
de 1,2km. 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Figura 21 – Conexión típica RS485 en serie 
3.4.9.2 
Instalación en lazo cerrado (bucle) 
• 
Realice la conexión 
RS485 del panel o 
periférico conectando el 
cable desde los terminales 
A y B (IN) de un lado del 
conector de la placa de un 
equipo a los terminales A 
y B (OUT) del otro lado de 
la placa en el siguiente 
equipo. 
• 
Realice esta conexión en 
todos los equipos, 
conectando siempre A con 
A y B con B. 
• 
Conecte el cableado de 
retorno desde los 
terminales libres del último 
equipo a los terminales 
libres del primer equipo. 
• 
La longitud máxima 
permitida del lazo 
completo es de 1,2km. 
 
 
 
B A B A
 
+ 
 
 
Figura 22 – Conexión típica RS485 en bucle 
RFL
RFL
B A B A
RFL
RFL
B A B A
```

**[F3]** `ZXSe` · *Tabla 4 – Lista de equipos periféricos compatibles* · `MIE-MI-600` p.29 · sim 0.8

```
Tabla 4 – Lista de equipos periféricos compatibles

Tabla 4 – Lista de equipos periféricos compatibles

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 27 
3.4.8 Lazo de equipos periféricos 
EN54
!

EN54-2 12.5 
Integridad de los 
canales de 
transmisión: 
La red no 
proporciona la 
integridad requerida 
respecto a los 
canales de 
transmisión. 
• 
Los paneles ZX1Se, ZX2Se, ZX5Se admiten una serie de equipos 
conectados al lazo periférico. 
• 
El lazo periférico utiliza el puerto ‘D’ de la placa base. 
• 
Un lazo periférico necesita que el panel tenga instalada una tarjeta 
aislada RS485. 
• 
La conexión de comunicaciones periféricas RS485 puede 
realizarse en lazo abierto o cerrado. Si desea más detalles, 
consulte el manual suministrado con la tarjeta RS485. 

• 
Cada equipo supervisado debe tener una dirección. Las 
direcciones posibles son de 1 a 126. Revise el manual de cada 
equipo para ver las direcciones posibles. 
• 
El número máximo de equipos conectados al lazo periférico es 31. 

Referencia 
Descripción del equipo 
Supervisado
709-601-001 
Repetidor remoto activo (repetidor)  
ZXr-A  
SÍ 
709-701-001 
Repetidor remoto pasivo (repetidor)  
ZXr-P.  
No supervisado si está ajustado a la dirección 0. 
Opcional 
709-001 
Anunciador remoto activo (repetidor)  
ZXR5B 
SÍ 
709-101 
Anunciador remoto pasivo (repetidor)  
ZXR4B 
NO 
795-015 
Módulo de 4 sirenas  
EXP-015 
SÍ 
795-065 
Placa de 40 leds de zona remotos  
EXP-065 
SÍ 
795-014 
Módulo de  relés  
EXP-014 
SÍ 
795-029 
Módulo de 8 entradas  
EXP-029 
SÍ 
795-057 
Interfaz MODBUS  
SÍ 
Tabla 4 – Lista de equipos periféricos compatibles
Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 28 
3.4.9 Conexión RS485  
EN54
!

EN54-2 12.5 
Integridad de los trayectos 
de transmisión: 
La red no proporciona la 
integridad requerida 
respecto a los trayectos de 
transmisión. 
• 
Los diagramas siguientes indican el cableado de instalaciones en 
lazo abierto o cerrado de la red de centrales y de los equipos del 
lazo de periféricos. 
• 
El cable RS-485 debe ser específico. Consulte la Sección Cables 
reco
[… contenido truncado para legibilidad]
```

**[F4]** `ZXe` · *EN54* · `MIE-MI-530rv001` p.34 · sim 0.8

```
EN54
!

MORLEY-IAS 
 
Paneles de Incendio ZX2e / ZX5e 
 
Página 34 de 50 
Documento No.MIE-MI-530, Revisión: 001,  
Manual de Instalación 
3.5.2.1.2 
Puente de Tensión de Lazo ZX5e  
La tabla anexa indica la posición de los Puentes de tensión de lazo J1 y J2 en el panel ZX5e, para 
equipos de Morley-IAS y System Sensor. Para otros fabricantes, consulte con su proveedor. 
 
Loop Driver 
J1 Position
J2 Position
Morley-IAS 
Abierto 
Cerrado 
System Sensor 
Abierto 
Cerrado 
Tabla 5 – Puentes de selección de tensión de lazo ZX5e 
 
 
Asegúrese de que el Puente de selección de tensión ha sido colocado en la posición 
correcta antes de alimentar el panel. En caso contrario, los equipos y el sistema podrían 
dañarse o no funcionar correctamente. 
 
 
3.5.3 Placas de comunicaciones RS485 / RS232 
 
EN54
!
 
EN54-2 12.5 
Integridad de las 
partes del sistema: 
La red de centrales 
no cumple los 
requerimientos de 
integridad como 
único sistema. 
• 
El sistema puede expandirse, mediante la conexión a centros de 
control (Integración), conexión de equipos periféricos, (repetidores, 
impresoras, placas de entrada o salida, etc.) o para interconexión 
de centrales en red. 
• 
El panel ZX2e dispone de 2 puertos (Puertos C y D), para la 
conexión de placas aisladas RS-485 o puerto serie RS-232. 
• 
El panel ZX5e, dispone de 3 puertos (Puertos B, C y D) 
identificados como PL2, PL3 y PL4 respectivamente.) ), para la 
conexión de placas aisladas RS-485 o puerto serie RS-232. 
 
 
• 
Puerto D (Periféricos): Permite la conexión de una tarjeta RS485 
para la conexión de hasta 31 equipos periféricos como 
Repetidores bidireccionales o no, Impresoras Remotas, Placas de 
8 entradas, Placas de 4 Salidas, Interface Mod-Bus, placa de 40 
salidas de Led de zona para sinóptico y placa Hi-485. 
• 
El Puerto C (Comunicaciones): Permite la conexión de centrales 
en red con placa RS-485 o la integración de centrales aisladas en 
software gráfico con placa RS-232. 
• 
El Puerto B (Comunicaciones): Permite la conexión de centrales en 
red a una red superior con placa RS-485 o la integración en 
software gráfico de centrales en red con placa RS-232.
```

**[F5]** `ZXe` · *Detección y señalización de fallos de Fuente* · `MIE-MI-530rv001` p.7 · sim 0.8

```
Detección y señalización de fallos de Fuente

Paneles de Incendio ZX2e / ZX5e 
 
MORLEY-IAS 
 
Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 7 de 50 
 
1.4 Información EN54 
EN54
9
 
• 
Este panel de control contra incendios cumple con los requerimientos de EN54-2/4 
1997. Adicionalmente sobre los requerimientos básicos obligatorios de la norma 
EN54, el panel dispone de las siguientes opciones reguladas. 
 
Funciones opcionales 
Cláusula EN54-2  
 
Indicación: 
Averías de puntos 
Controles: 
Detección por coincidencia 
 
Retardos de activación de Salidas 
 
Anulación de cada punto direccionable 
 
Prueba 
Salidas: 
Salidas para equipos de incendio 
 
8.3 
7.12 
7.11 
9.5 
10 
7.8 
 
 
 
EN54
9
 
• 
La Fuente de alimentación de los paneles ZX2e y ZX5e cumplen con los siguientes 
requerimientos de la norma EN54-4. 
 
Funciones Fuente de Alimentación ZX2e & ZX5e 
Cláusula EN54-4 
 
Alimentación derivada de la Fuente principal 
Alimentación derivada de Baterías en reposo 
Carga y monitorización de Baterías en reposo 
Detección y señalización de fallos de Fuente 
5.1 
5.2 
5.3 
5.4 
 
EN54
N/A
 
• 
Adicionalmente, sobre las funciones requeridas por la norma EN54-2, el panel 
dispone de las siguientes opciones adicionales, no reguladas por la norma: - 
 
Opciones Adicionales 
Sección del Manual 
 
Salida Auxiliar de alimentación 24Vcc 
3.4.6 
 
Puerto C de comunicaciones para Red/Integración 
3.4.7, 3.5.1.1 y 3.5.1.2 
 
Puerto B de comunicaciones para enlace Red/Red o 
Red/Integración (solo ZX5e) 
3.4.7.2, 3.4.7.3, 3.5.1.1 y 
3.5.1.3 
 
Puerto D para equipos periféricos 
3.4.8, 3.5.1.1 y 3.5.1.3 
 
Lazo de comunicaciones Hi-485 para enlace de redes de 
centrales 
3.4.10 y Manual de Instalación 
Hi485  
 
Salidas auxiliares de relé 
3.4.5 
 
Opción de Impresora (solo ZX5e) 
3.5.4 
 
Entrada de disparo de sirenas 
3.4.12 
 
Grupos de desconexión 
3.4.11
```

### Respuesta del bot

```
Debo ser directo contigo: **los fragmentos disponibles no contienen un procedimiento paso a paso de sustitución de ZXe por ZXSe**.

Lo que sí puedo extraer de los fragmentos para orientarte en las diferencias de conexionado relevantes:

---

## Diferencias de conexionado ZXe → ZXSe que debes tener en cuenta

### Circuitos de sirenas
- **ZX1Se / ZX2Se**: **2 circuitos de sirena** supervisados (A y B), corriente máxima **1 A entre ambos circuitos** [F1]
- **ZX5Se**: **4 circuitos de sirena** supervisados (A, B, C y D), corriente máxima **2 A entre los 4 circuitos** [F1]
- Resistencia de final de línea obligatoria: **6k8, 0,5 W mínimo (Ref: 170-073-682)** en la última sirena de cada circuito [F1]
- Cada sirena debe tener **diodo integrado** para supervisión [F1]

### Lazo periférico RS485
- Los paneles **ZX1Se, ZX2Se, ZX5Se** admiten hasta **31 equipos** en el lazo periférico, usando el puerto **'D'** de la placa base [F3]
- Requiere tarjeta aislada RS485 instalada [F3]
- Longitud máxima del cableado RS485: **1,2 km** (lazo abierto o cerrado) [F2]
- Resistencias de final de línea RS485: **150 Ω, 0,5 W mínimo (P/N 170-073-151)** [F2]

### Puertos de comunicaciones (ZXe como referencia)
- El **ZX2e** dispone de **2 puertos** (C y D) [F4]
- El **ZX5e** dispone de **3 puertos** (B, C y D) [F4]
- Verifica que la ZXSe equivalente mantiene la misma arquitectura de puertos antes de reutilizar el cableado existente

---

## ⚠️ Lo que NO está en los fragmentos

- Procedimiento de migración/sustitución física paso a paso
- Compatibilidad directa de detectores convencionales ZXe → ZXSe
- Configuración de zonas convencionales en ZXSe
- Dimensiones de caja / compatibilidad de montaje

**Para el procedimiento completo de sustitución, consulta:**
- Manual de instalación ZXSe **MIE-MI-600** (sección de puesta en marcha)
- Manual de instalación ZXe **MIE-MI-530 rev. 001** (para comparar terminales)
- Soporte técnico Morley-IAS para confirmar compatibilidad de detectores existentes

---

Fuente: MIE-MI-600 (sin revisión registrada); MIE-MI-530, Revisión 001

También puedo ayudarte con: **conexionado de sirenas en ZXSe**, **configuración del lazo periférico RS485** o **especificaciones de alimentación y baterías de la ZXSe**.
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** El bot admite correctamente que no existe en los fragmentos un procedimiento paso a paso de sustitución ZXe→ZXSe (admit_no_info honesto), redirige al técnico a los manuales correctos y al soporte Morley-IAS, y las afirmaciones técnicas complementarias que ofrece (circuitos de sirena, resistencias EOL, lazo RS485, puertos de comunicaciones) están todas soportadas por los fragmentos F1, F2, F3 y F4 que cita. No hay alucinaciones ni miscitaciones detectables.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL
- **Dimensión equivocada(s) del judge** (si aplica):
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (multi-manual):**

Migración ZXe -> ZXSe (intra-Morley). Cruzando MIE-MI-530 (ZXe) y MIE-MI-600 (ZXSe). Verificado con grep que el MIE-MI-600 NO contiene procedimiento de migración desde ZXe (no menciona "ZXe" en su texto). El corpus no tiene un procedimiento paso a paso documentado para esta migración. Lo que SÍ permite es comparar arquitecturas de conexionado entre ambos manuales — el bot lo hace correctamente.

**Calidad de los chunks:**

- F1, F2, F3 del MIE-MI-600 (ZXSe). F4, F5 del MIE-MI-530 (ZXe). Diversidad correcta.
- Chunks razonablemente limpios; F3 contiene tabla de equipos periféricos compatibles ZXSe legible.
- F4 menciona "Loop Driver J1 J2 Position — Morley-IAS / System Sensor" relevante.

**Comparación con bot:**

- El bot SÍ combinó F1+F2+F3 (ZXSe) con F4 (ZXe) y extrajo diferencias relevantes de conexionado.
- Conducta observada `answer` con disclaimer honesto al inicio.
- Es probablemente la mejor respuesta de los 8 casos en términos de uso multi-manual.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** behavior_match es discutible (expected admit_no_info, observed answer híbrido).
- **Nota / por qué:** Recalibrado legítimo: el corpus no tiene procedimiento explícito ZXe -> ZXSe (verificado con grep). Pero el bot no debería ser penalizado por dar info útil del conexionado de ambos manuales — su respuesta híbrida es mejor que admit_no_info puro. El judge acierta dando PASS.
- **Origen del problema:** ninguno significativo; ejemplo de bot funcionando bien en multi-manual intra-marca cuando los F llegan correctos.
