# Calibración del judge v2 — categoría `not_in_db` (8 preguntas)

**Origen:** `logs/eval_20260502T152857Z.json` (eval del 2 mayo 2026).

**Categoría:** Producto/fabricante NO en corpus -> bot debe admitir el gap sin inventar.

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

## nd001 — judge dice **PASS ✓** · (1/8)

**Pregunta del técnico:** ¿Cómo programo la central Bosch Avenar FPA-1200?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 4/4 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Bosch no está en la BD. Bot debe reconocerlo sin inventar. forbidden_keywords: 'menú' y 'procedimiento' retirados — son palabras que pueden aparecer en una respuesta honesta ('prueba el menú principal'); sustituidos por señales inequívocas de que el bot inventó un procedimiento ('paso 1', 'paso 2', 'pulsa enter')._

### Fragmentos que el bot usó (top 5)

**[F1]** `ID2000` · *2 Conexión/configuración* · `MPDT180` p.12 · sim 0.74

```
2
Conexión/configuración

2
Conexión/configuración

Panel ID2000 - Manual de programación
Conexión/configuración
MP-DT-180
       NOTIFIER ESPAÑA
       7
b
a
1
+ -
+
12V
12V
-
+
230 V AC
50/60 Hz
-
A
A
B
2
3
?
2
Conexión/configuración
Para conectar el sistema, proceda como se indica a
continuación:
1
Conecte los dos cables (A) del interior del panel a las
dos baterías de plomo ácido selladas de 12 V y, a
continuación, coloque sólo un extremo del cable
blanco suministrado (B).
2
Conecte la fuente de alimentación.
3
Conecte el cable blanco al terminal que queda libre -
consulte el apartado a. (a continuación).
Una vez terminadas las conexiones, la pantalla muestra
el mensaje de descripción de producto junto con el número
de la versión de software.
Pasados unos segundos, aparece la pantalla de primer
nivel, indicando que el panel ya está preparado para
aceptar instrucciones de configuración.
Si se conecta un PC, la pantalla de primer nivel se muestra
en la pantalla del PC.
Recuerde que....
a. Si no ha finalizado las conexiones de las baterías en
60 segundos después de haber conectado la fuente
de alimentación principal, el panel indicará un fallo de
cargador/batería y mostrará el siguiente mensaje:
Avería de baterías
y se activará el zumbador interno. Se iluminarán los
leds de FALLO y FALLO ALIMENTACIÓN. Si es así:
i
Pulse la tecla SILENCIAR ZUMBADOR o ACEPTAR
para silenciar el zumbador y, sólo después de finalizar
todas las conexiones, pulse REARME para eliminar
la condición de avería.
b. Si el panel no se ha configurado con ningún dato de
sensor o módulo, en pantalla aparecerá el siguiente
mensaje:
LA CENTRAL NO ESTÁ CONFIGURADA
Consideraciones especiales para conectar una red
Se recomienda lo siguiente:
i
Para configurar un panel (directamente o utilizando el
programa
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *El parpadeo del led indica que estamos en el menú de Zona de entrada.* · `MIE-MI-100` p.33 · sim 0.70

```
El parpadeo del led
indica que
estamos en el menú de Zona de
entrada.

El parpadeo del led
indica que
estamos en el menú de Zona de
entrada.

Central HRZ 2-8 - Manual de instalación, puesta en marcha y configuración
MIE-MI-100
                     MORLEY-IAS
27
Acceso con teclas 
  + 
, parpadeo LED 
 y 
.
Se pueden seleccionar las siguientes opciones:
a. Borrar Checksum
b. Seleccionar configuración por defecto
7.3.1
Borrar Checksum (registro de incidencias en los
datos de la memoria interna)
Seleccionar con tecla 
Utilice esta opción para borrar las averías de checksum
de la configuración de usuario.
7.3.2
Seleccionar configuración por defecto
Seleccionar con tecla 
Con esta función, la central vuelve a la configuración por
defecto de fábrica. Cuando el led de sistema 2 está
iluminado (led 
 =ON), significa que la central está con
la configuración por defecto; si está apagado (led 
=OFF), significa que ha habido un cambio en la
configuración.
7.4
Tipo de entrada de zona de alarma
Acceso con tecla  
  desde configuración
Las zonas de entrada se pueden configurar según se indica
a continuación:
Seleccionar zona (n) con la tecla 
, LED 
 de
zona de alarma (fuego)
a.
Alarmas enclavadas/no enclavadas
b.
Alarma por cortocircuito
c.
Funcionamiento automático o manual
d.
Detección por coincidencia de alarmas o alarmas
independientes
e.
Retardo de verificación de Sprinkler.
f.
Tipo de equipo de final de línea (EFL).
7.4.1
Alarmas enclavadas/no enclavadas
Seleccionar con tecla 
, LED 
Una zona de detección se puede configurar como
enclavada (led 
=OFF) o no enclavada  (led 
=ON). Si
selecciona como enclavada, si la central entra en alarma
(o avería), esta condición permanecerá activa hasta que
se rearme la central. Si se selecciona como no enclavada,
la central vuelve a su estad
[… contenido truncado para legibilidad]
```

**[F3]** `PCD-100` · *2- Instalación 2- Installation* · `Manual_PCD-100 (55310009 MI 608 m 2024 b)` p.1 · sim 0.58

```
2- Instalación
2- Installation

ESPAÑOL
ENGLISH
MANUAL CALL POINT
PULSADOR CONVENCIONAL
PCD-100
PCD-100
1- Introducción
1- Introduction
El pulsador convencional esta diseñado en base a la 
actual Norma Europea UNE EN54-11. Se dispone de la 
correspondiente Certificación de producto.
Es compatible con los distintos sistemas de detección de 
incendio, existentes en el mercado.
La indicación de Disparado se hace visible con una  pestaña 
de color amarillo que emerge en la ventana de activación , 
indicando la condición de ALARMA
The manual call point is designed according to de European 
regulation EN54-11. It is available the relevant certificate of 
the product.
The manual call point is compatible with the different type of 
detection systems in the market.
The activated indication is visible with a flap that rises in the 
activation window, indicating the state of PUSHED.
La instalación y ubicación de los pulsadores debe hacerse 
según la norma UNE 23.007 parte 14.
Installation and placement of call points must be done 
according to regulation UNE 23.007 - 14
Es aconsejable el mantenimiento y verificación de los mismos 
como mínimo una vez al año, de esta forma se asegura la 
vida del pulsador.
It is advisable to perform maintenance and verification of call 
points at least once a year in order to ensure the right running.
2- Instalación
2- Installation
5- Rearme del pulsador
5- Reset of call point
4- Prueba y mantenimiento
4- Test and maintenance
3- Características Técnicas
3- Technical features
Modelo de Referencia
Características Medioambientales
•	Temperatura trabajo
-10 a 50ºC
•	Temperatura almacén
-10 a 70ºC
•	Humedad relativa
95% sin cond.
•	Nominal IP (uso interno)
IPX0
Características Módulo
•	Tensión alimentación
0 - 30VCA
•	Consumo en reposo
0 mA
•	Resistenci
[… contenido truncado para legibilidad]
```

**[F4]** `Serie 800` · *Cuando se aplica alimentación a la central se debe llevar a cabo la Configuración para iniciar el panel. Asegúrese que c* · `MIDT020` p.25 · sim 0.74

```
Cuando se aplica alimentación a la central se debe llevar a cabo la
Configuración para iniciar el panel. Asegúrese que conoce bien el
procedimiento antes de empezar (consulte la página siguiente). (continuación)

21
MI-DT-020
NOTIFIER ESPAÑA, S.A.
Introducción
Cuando haya finalizado la instalación, puede poner en marcha el sistema
y probarlo. Para asegurar una puesta en marcha sin problemas, siga las
instrucciones siguientes paso a paso.
Comprobaciones preliminares
Antes de conectar cualquier circuito auxiliar, es recomendable que se
active el panel y se pruebe. Una vez el panel funciona sin averías
presentes, los circuitos se pueden conectar de uno en uno y rectificar
las averías asociadas antes de proceder con el siguiente circuito.
Asegúrese que todos los fusibles permanecen en su sitio e intactos, y
que los módulos adicionales están correctamente instalados y tienen las
conexiones configuradas para funcionar según lo requerido.
Compruebe que el cable de cinta se ha vuelto a conectar a la tarjeta
procesadora y que la conexión AC del transformador está firmemente
conectada en conector de la PCB principal.
Asegúrese que existe en el conector J16 un puente entre los terminales
5 y 3 cuando no existe fuente de alimentación remota. Ver figura 9 de la
página 25.
Nota. No es posible inhibir la condición de avería de la batería instalando
una resistencia temporal en los terminales de la batería. Por lo tanto,
cuando el panel esté conectado, debe conectar una batería para habilitar
la función de configuración.
Instale los equipos de Final de Línea a todas las entradas y salidas
relevantes. Los terminales incluyen conectores que se suministran con
la central. Instale el equipo apropiado (Unidad de Final de Línea,
resistencia de 4K7 ó 10K) en los bloques de terminales pelados y
[… contenido truncado para legibilidad]
```

**[F5]** `ECO1005` · ** ECO1000(D)B, ECO1000(D)BSD* · `I56-1652-023 ECO1005_ECO1005T_ECO1004T` p.1 · sim 0.70

```
*
ECO1000(D)B,
ECO1000(D)BSD (continuación)

[TABLA EXTRAÍDA]
|  |  |  | ECO10 | 05 | , E | CO1005T |  | WARNING - Remove power from se SENSOR INSTALLATION | nsor monitoring circuits befo | re installing sensors.
----------------------------------------
 |  |  |  | and | E | CO | 1004T |  | 1. Place the sensor into the sensor ba | se and rotate clockwise with ge | ntle pressure until the
 | 0832 | Declar ECO1 | ation of Per 004T: 0832 | formance Reference: -CPD-0068 EN54-5: C | lass | BS | 0832 |  | sensor drops into place. Continue lines up with the lines moulded in th | rotating clockwise until the sl e base (See fig 1 **). | ot in the sensor cover
 | 17 | ECO1 ECO1 | 005: 0832 005T: 0832 | -CPD-0066 EN54-5: C -CPD-0067 EN54-5: C | lass lass | A1R A2S | 17 |  | 3. After all sensors have been install 4. Test the sensor as described unde Tamper-Resistance | ed, apply power to the sensor m r TESTING. | onitoring circuits.
 |  |  |  |  |  |  |  |  | The removal of the small plastic tab o | n the base indicated in figure 1 | prevents the removal
 |  |  |  | m |  |  |  |  | of the sensor head without a tool. |  | 
 |  |  |  | m |  |  |  |  |  |  | 
 |  |  |  | 0 5 |  |  | 70°C |  | TESTING |  | 
 |  |  | 1 | 02 mm |  |  |  |  | Heat Method |  | 
 |  |  |  |  |  |  | -30°C |  | 1. Using a heat tool from an approved in accordance with the suppliers in | manufacturer such as No Clim structions | b Products Ltd, apply
 |  |  |  |  |  |  |  |  | 2. The red LED on the sensor should | latch into alarm within 40 sec | onds, and the control
 |  |  |  |  |  |  |  |  | panel should activate into alarm. |  | 
 |  |  |  | 70g |  |  |  |  | Laser Test Tool Method (Model N | o. ECO1000RTU) | 
 |  |  |  |  |  |  |  |  | Note: This method does not carry out | a complete functional test of t
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre la central **Bosch Avenar FPA-1200** en mi base de documentación. Los fragmentos disponibles no contienen ningún manual ni dato técnico de ese producto.

Consulta directamente la documentación técnica oficial de Bosch para la programación de esa central.
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

**Razón del judge:** Ningún fragmento F ni V contiene información sobre la central Bosch Avenar FPA-1200; el bot admite correctamente que no dispone del manual y redirige al técnico a la documentación oficial del fabricante, lo cual es la conducta esperada (admit_no_info) y constituye una respuesta honesta y útil.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Bosch no es fabricante cubierto en el corpus (verificado: ningún manual menciona "Bosch", "Avenar" o "FPA-1200"). El bot debe admitir el gap y derivar a documentación oficial de Bosch.

**Calidad de los chunks:**

- Los 5 F traídos son verdaderamente irrelevantes: cubren ID2000 (Notifier), HRZ 2-8 (Morley), PCD-100 (pulsador convencional Detnov), Serie 800 (Notifier) y ECO1005 (Apollo/System Sensor) — todos productos PCI distintos al pedido. No hay miss de retrieval enmascarado.
- Patrón de chunks: similitudes 0.58-0.74. El bot recibe ruido razonable de "central + configuración", pero ningún chunk de Bosch.

**Comparación con bot:**

- Admitió "no tengo info" correctamente y con nombre del producto explícito.
- No alucinó procedimientos ni inventó pasos (forbidden_keywords cubiertos).
- Derivó a fuente externa (documentación oficial Bosch) — acción concreta.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo, corpus gap real. Respuesta concisa y honesta.
- **Origen del problema:** Corpus gap legítimo (Bosch fuera de catálogo Fontiber).

---

## nd002 — judge dice **PASS ✓** · (2/8)

**Pregunta del técnico:** Mi Esser IQ8Quad da error 14

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/2 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Esser no está en la BD. Debe admitir. forbidden_keywords: 'probablemente' retirado — palabra común que puede aparecer en respuesta honesta ('probablemente tendrás que consultar al fabricante'); reforzado con dos variantes de claim falso sobre el error._

### Fragmentos que el bot usó (top 5)

**[F1]** `ID50/60` · *Apéndice 3 - Mensajes de avería* · `MIDT156` p.115 · sim 0.74

```
Apéndice 3 - Mensajes de avería

Apéndice 3 - Mensajes de avería

Apéndice 3 - Mensajes de avería
MI-DT-156_C
   A3- 1
Centrales ID50/60 - Manual de instalación, puesta en marcha y configuración
Apéndice 3
Mensajes de avería.
Posibles causas y soluciones
Instalación del cableado del lazo
LAZO CIRCUITO ABIERTO - El cableado del lazo tiene una
desconexión. Acción: Compruebe las conexiones de cableado de la
central. Si éstas son correctas y el problema persiste, desconecte el
cableado del lazo y short out the outgoing and incoming (+ve to +ve
and -ve to -ve) connectors. Si el fallo desaparece, significa que la
circuitería del lazo de la placa está bien. Compruebe entonces la
conexión del cableado a todos los equipos del lazo.
LAZO CORTOCIRCUITO - Se ha producido un cortocircuito entre la
central y el aislador. Si los aisladores están instalados, el sistema
muestra el mensaje “EQUIPO NO RESPONDE” en todos los equipos
situados entre los puntos aislados. Desconecte la sección afectada
del lazo y utilice un multímetro para comprobar las secciones del
cableado del lazo.
DERIVACION EN LAZO O EN EQUIPO - La supervisión de avería
en el lazo ha detectado un valor de impedancia del cableado fuera
del rango aceptable para que el lazo funcione correctamente. Acción:
Desconecte el cableado del lazo a la central y utilice un multímetro
para comprobar las secciones del cableado del lazo.
RESPUESTA INCORRECTA LAZO - Se ha detectado una avería
interna en el circuito del controlador del lazo. Acción: Sustituya la
placa base.
EQUIPO NO RESPONDE - Un equipo del lazo no responde,
posiblemente debido a una configuración incorrecta. Acción:
Configura el equipo que falta o bien vuelva a configurar los equipos
del lazo.
DIRECCION DUPLICADA - Hay dos equipos en el lazo con la misma
dirección. Acció
[… contenido truncado para legibilidad]
```

**[F2]** `ID50/60` · *Apéndice 3* · `MIDT156` p.115 · sim 0.74

```
Apéndice 3

Apéndice 3

Apéndice 3 - Mensajes de avería
MI-DT-156_C
   A3- 1
Centrales ID50/60 - Manual de instalación, puesta en marcha y configuración
Apéndice 3
Mensajes de avería.
Posibles causas y soluciones
Instalación del cableado del lazo
LAZO CIRCUITO ABIERTO - El cableado del lazo tiene una
desconexión. Acción: Compruebe las conexiones de cableado de la
central. Si éstas son correctas y el problema persiste, desconecte el
cableado del lazo y short out the outgoing and incoming (+ve to +ve
and -ve to -ve) connectors. Si el fallo desaparece, significa que la
circuitería del lazo de la placa está bien. Compruebe entonces la
conexión del cableado a todos los equipos del lazo.
LAZO CORTOCIRCUITO - Se ha producido un cortocircuito entre la
central y el aislador. Si los aisladores están instalados, el sistema
muestra el mensaje “EQUIPO NO RESPONDE” en todos los equipos
situados entre los puntos aislados. Desconecte la sección afectada
del lazo y utilice un multímetro para comprobar las secciones del
cableado del lazo.
DERIVACION EN LAZO O EN EQUIPO - La supervisión de avería
en el lazo ha detectado un valor de impedancia del cableado fuera
del rango aceptable para que el lazo funcione correctamente. Acción:
Desconecte el cableado del lazo a la central y utilice un multímetro
para comprobar las secciones del cableado del lazo.
RESPUESTA INCORRECTA LAZO - Se ha detectado una avería
interna en el circuito del controlador del lazo. Acción: Sustituya la
placa base.
EQUIPO NO RESPONDE - Un equipo del lazo no responde,
posiblemente debido a una configuración incorrecta. Acción:
Configura el equipo que falta o bien vuelva a configurar los equipos
del lazo.
DIRECCION DUPLICADA - Hay dos equipos en el lazo con la misma
dirección. Acción: Cambiar la dirección de uno de los dos
[… contenido truncado para legibilidad]
```

**[F3]** `ID2000` · *Avería de sistema - Avería de LIB-CPU Avería del driver LIB Avería central 5 - Reinicio de alimentación Avería de sistem* · `MIDT180` p.59 · sim 0.73

```
Avería de sistema - Avería de LIB-CPU
Avería del driver LIB
Avería central 5 - Reinicio de alimentación
Avería de sistema 29 - Avería Checksum LIB ROM

Avería de sistema - Avería de LIB-CPU
Avería del driver LIB
Avería central 5 - Reinicio de alimentación
Avería de sistema 29 - Avería Checksum LIB ROM

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
dirección no válida, es decir se ha dejado la dirección ‘00’
de fáb
[… contenido truncado para legibilidad]
```

**[F4]** `ID2000` · *1.1 Mensajes de avería - Causas posibles y soluciones* · `MIDT180` p.59 · sim 0.73

```
1.1
Mensajes de avería - Causas posibles y
soluciones

1.1
Mensajes de avería - Causas posibles y
soluciones

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
dirección no válida, es decir se ha dejado la dirección ‘00’
de fábrica.
```

**[F5]** `ID50/60` · *Instalación del cableado del lazo* · `MIDT156` p.115 · sim 0.73

```
Instalación del cableado del lazo

Instalación del cableado del lazo

Apéndice 3 - Mensajes de avería
MI-DT-156_C
   A3- 1
Centrales ID50/60 - Manual de instalación, puesta en marcha y configuración
Apéndice 3
Mensajes de avería.
Posibles causas y soluciones
Instalación del cableado del lazo
LAZO CIRCUITO ABIERTO - El cableado del lazo tiene una
desconexión. Acción: Compruebe las conexiones de cableado de la
central. Si éstas son correctas y el problema persiste, desconecte el
cableado del lazo y short out the outgoing and incoming (+ve to +ve
and -ve to -ve) connectors. Si el fallo desaparece, significa que la
circuitería del lazo de la placa está bien. Compruebe entonces la
conexión del cableado a todos los equipos del lazo.
LAZO CORTOCIRCUITO - Se ha producido un cortocircuito entre la
central y el aislador. Si los aisladores están instalados, el sistema
muestra el mensaje “EQUIPO NO RESPONDE” en todos los equipos
situados entre los puntos aislados. Desconecte la sección afectada
del lazo y utilice un multímetro para comprobar las secciones del
cableado del lazo.
DERIVACION EN LAZO O EN EQUIPO - La supervisión de avería
en el lazo ha detectado un valor de impedancia del cableado fuera
del rango aceptable para que el lazo funcione correctamente. Acción:
Desconecte el cableado del lazo a la central y utilice un multímetro
para comprobar las secciones del cableado del lazo.
RESPUESTA INCORRECTA LAZO - Se ha detectado una avería
interna en el circuito del controlador del lazo. Acción: Sustituya la
placa base.
EQUIPO NO RESPONDE - Un equipo del lazo no responde,
posiblemente debido a una configuración incorrecta. Acción:
Configura el equipo que falta o bien vuelva a configurar los equipos
del lazo.
DIRECCION DUPLICADA - Hay dos equipos en el lazo con la misma
dirección. A
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre el **Esser IQ8Quad** en mi base de documentación. Los fragmentos recuperados corresponden únicamente a centrales **Notifier ID50/60** [F1] e **ID2000** [F3], que son productos distintos.

El código de error 14 del IQ8Quad no aparece en ninguno de los fragmentos disponibles, y no puedo interpretarlo sin la documentación específica de Esser.

**Consulta directamente la documentación técnica del fabricante Esser (Honeywell) para el IQ8Quad**, o contacta con el soporte técnico de Esser para obtener la interpretación correcta del error 14.
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

**Razón del judge:** El bot identifica correctamente que ningún fragmento F ni V cubre el producto Esser IQ8Quad ni su error 14 — todos los fragmentos disponibles corresponden a Notifier ID50/60 e ID2000. La cita a [F1] y [F3] es precisa y solo para identificar qué productos sí están cubiertos, no para afirmar datos técnicos sobre el IQ8Quad. Admitir la ausencia de información y redirigir al fabricante es la conducta esperada (admit_no_info) y resulta genuinamente útil para el técnico.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Esser (marca Honeywell) y el IQ8Quad no figuran en el corpus (verificado: 0 hits en manuales). El error 14 del IQ8Quad es código propietario Esser; el bot debe admitir el gap y derivar.

**Calidad de los chunks:**

- Los 5 F son irrelevantes para Esser: traen apéndices de mensajes de avería de Notifier ID50/60 e ID2000. Es un retrieval razonable por similitud léxica ("error"/"avería"/"mensaje"), pero ningún chunk cubre el IQ8Quad. Sin retrieval miss oculto.

**Comparación con bot:**

- Admitió "no tengo info" correctamente identificando además los productos que SÍ cubren los F (ID50/60 e ID2000).
- No alucinó significado del error 14 (forbidden_keywords cubiertos).
- Derivó a fabricante (Esser/Honeywell) — útil y honesto.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo. Bonus: el bot usa las citas [F1] y [F3] sólo para identificar qué productos sí están cubiertos, no para inventar info sobre Esser. Buena práctica.
- **Origen del problema:** Corpus gap legítimo (Esser fuera de catálogo).

---

## nd003 — judge dice **PASS ✓** · (3/8)

**Pregunta del técnico:** ¿El detector Apollo XP95 es compatible con la ID3000?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Apollo no está; debe admitir el gap del Apollo aunque la ID3000 sí esté._

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Panel ID3000 - Manual de programación* · `MPDT190` p.136 · sim 0.73

```
Panel ID3000 - Manual de programación

Panel ID3000 - Manual de programación

Apéndice 2
Panel ID3000 - Manual de programación
MP-DT-190_D
   A2-1
Apéndice 2
Equipos de lazo disponibles
1
Tipos de equipo
La ID3000 es compatible con los siguientes equipos que
utilizan protocolo de comunicaciones Notifier:
Sensores analógicos:
a. VIEW (humo láser)
FSL-751E
b. Optiplex
(Comb. térmico/humo)
SDX-751TEM
c. Iónico
CPX-751E
d. Óptico
SDX-751EM
e. Óptico intrínsecamente
seguro HAZARD
IDX-751
f. HARSH/FILTREX (Óptico)
HPX-751E
g. Térmico (Tipo A1)
FDX-551EM
h. Térmico (Tipo BS)
FDX-551THEM
i. Térmico-Térmovelocimétrico
(Tipo A1R)
FDX-551REM
Módulos:
a. Pulsador manual (PUL)
M700KAC
b. Pulsador manual
impermeable. IP65
M700KACW
c. Módulo monitor (CDI)
ZMX-1E/MMX-2/M710-CZ
d. Módulo monitor
MMX-1E, M701, M720
e. Módulo monitor (Micro)
MMX-102E
f. Módulo monitor
MMX-10
(10 entradas)
g. Circuito supervisado
(para sirenas)
CMX-2E, M701, M721
h. Circuito supervisado (para
equipos de activación)
PS2-CMX
i. Interfaz de detector
convencional
CDI
j. Módulo de control (tarjeta
de relé de 10-vías)
CMX-10R
k. Sirena alimentada por lazo Tipo  AB**, AN**
l. Módulo de relé de
alimentación principal
M701-240
m.Módulo de relé de
alimentación principal en
montaje DIN
M701-240-DIN
Nota: El ZMX-1 es la alternativa económica del Módulo de control CDI. Sin embargo,
estos dos equipos no se pueden intercambiar a menos que se realice un cambio
de configuración en la central.
```

**[F2]** `ID3000` · *Véase la Sección 4.4.6.* · `MCDT190` p.33 · sim 0.80

```
Véase la Sección 4.4.6. (continuación)

[TABLA EXTRAÍDA]
|  |  |  | 4.7 | Segunda Vent | ana del M | ódulo | 
----------------------------------------
 |  |  |  |  | Igual que para lo | s detectore | s, se pued | e acceder a la
 |  |  |  |  | información que | define los | módulos a | través de dos
 |  |  |  |  | ventanas. |  |  | 
 |  |  |  |  | Puede cambiar d | e ventana pu | lsando la te | cla de función
 |  |  |  |  | <F2>. En la segu | nda ventana | encontrar | á columnas de
 |  |  |  |  | SENSIBILIDAD, R | ETARDOS, | PRIORIDA | D y FUNCIÓN
 |  |  |  |  | ESPECIAL. Su si | gnificado se | explica en | las siguientes
 |  |  |  |  | secciones. |  |  | 
 |  |  |  | 4.7.1 | Sensibilidad |  |  | 
 |  |  |  |  | La opciones de su | pervisión par | a ALARMA | y AVERÍA están
 |  |  |  |  | ajustadas por def | ecto de fábr | ica. Estas c | ondiciones de
 |  |  |  |  | ON/OFF normalm | ente se dejan | en los valor | es por defecto,
 |  |  |  |  | sin embargo es p | osible que, | en algunas | circunstancias
 |  |  |  |  | especiales, neces | iten modifica | rse. Por eje | mplo, si se usa
 |  |  |  |  | un Módulo de Co | ntrol CMX c | omo salida | de relé libre de
s |  |  |  |  | tensión con las len | güetas rotas | , el umbral d | e averías para
o |  |  |  |  | el Circuito Abierto | debe estar | ajustado a | OFF. La opción
v |  |  |  |  | de supervisión de | ‘ALARMA’ p | ara un Pulsa | dor Manual no
i |  |  |  |  | puede ajustarse a | OFF. |  | 
h |  |  |  |  |  |  |  | 
c |  |  |  |  | Los ajustes de sen | sibilidad par | a el tipo de | módulo ‘ASPR’
r |  |  |  |  | son iguales que p | ara otros m | ódulos, a e | xcepción de la
A |  |  |  |  | opción de PREAL | ARMA que | está situada | en la columna
 |  |  |  |  | titulada ‘S/C.’ (co | rto circuito) | y la opció | n de ‘AVE
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *Test: todos sensores* · `MIDT1450` p.8 · sim 0.80

```
Test: todos sensores

Test: todos sensores

Vía radio. Manual de instalación
MI-DT-1450_A
        8 de 14
Editar dirección del lazo:
Para poder proporcionar la máxima flexibilidad al sistema vía radio, cada uno de los detectores del 2100RFE–
AS conectado al FLG2100 es considerado por la central de detección de incendios como una única
dirección de detector; cada pulsador manual es considerado como una única dirección de módulo, y el
propio FLG2100, como otra dirección de módulo. Cuando se configuran inicialmente los dispositivos, se
crean con direcciones secuenciales partiendo de S1 (Sensores) o M1 (FLG2100 y Pulsadores manuales).
La función Editar direcc. lazo  sirve para poder modificar estas direcciones iniciales. Tenga en cuenta que
el M500RFE adquiere la dirección de módulo M1.
Cuando se selecciona Editar direcc. lazo, los dispositivos en el sistema FLG2100 vía radio se visualizarán
uno a uno, identificados por su número de serie y dirección de lazo actual.
1. Use las flechas para desplazarse hasta la unidad que desea editar, pulse entonces el Botón B para
seleccionarla. La dirección del dispositivo actual aparecerá tanto bajo la dirección antigua como la
nueva.
2. Introduzca la nueva dirección usando el teclado o las teclas con flecha y, a continuación, pulse  el Botón
B para aceptar.
3. La nueva dirección se visualizará bajo Nueva direc.Lazo. Pulse “Sí” (Botón B) para aceptar o "Volver"
para cancelar.
4. Repita los pasos del 1 a 3 para cualquier otra dirección que desee modificar, a continuación, pulse
“Volver (Botón A) para regresar al menú
Aviso: El FLG2100 ("Gateway") adquiere la primera dirección de módulo en el lazo (M1). Aunque
la dirección se puede modificar, tenga cuidado y no elimine el módulo. El sistema vía radio no
funcionará si el Interfaz FLG2100 ("
[… contenido truncado para legibilidad]
```

**[F4]** `ID3000` · *Información* · `TIDT108` p.1 · sim 0.80

```
Información

Información

Toda la información contenida en este documento puede ser modificada sin previo aviso 

Oficinas Centrales y Zona Este:T. 934 973 960 F. 934 658 635; Centro:T. 911 314 800  F. 911 314 899 
Norte:T. 944 802 625 F. 944 801 756; Sur:T. 954 187 011 F. 955 601 234; Portugal:T. 00 351218162636 F. 00 351218162637 
www.notifier.es 
1 de 2 
                                      Información   
TI 
Información técnica
TI-DT-108
18/01/2010

Centrales ID3000 
Características de la versión 4.6x 

Las centrales de la serie ID3000 se han renovado en muchos aspectos y, al mismo tiempo, 
también se han actualizado las certificaciones para cumplir los requisitos de la CPD 
(Directiva de Productos de la Construcción), obligatoria en todas las centrales de 
incendios que se vendan en el mercado Europeo desde el 1 de Agosto de 2009. En la 
medida de lo posible, se ha intentado que todos los productos y componentes de la serie 
ID3000 sean compatibles con las versiones anteriores por lo que una única gama de piezas 
de recambio sea suficiente para mantener o ampliar los sistemas. Aun así, hay algún 
producto que no se puede utilizar como recambio de versiones anteriores, sin embargo, en 
ningún caso esto supondrá la imposibilidad de mantener en funcionamiento un sistema.  

A continuación indicamos las novedades más importantes que se han implantado en las 
centrales ID3000. 

 
EN54-2 – Enmienda para la coincidencia de alarma 
 
EN54-2 – Enmienda para la reactivación tras silenciarse la alarma 
 
EN54-2 – Enmienda para las anulaciones de las sirenas 
 
EN54-3 – Prueba de la supervisión de sirenas no direccionables 
 
El Firmware es compatible con todas las versiones anteriores 

La especificación de coincidencia (a veces conocida como la “doble activación o 
co
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000 Repetidor` · *2.8 Instalación del Cableado* · `MNDT200` p.19 · sim 0.80

```
2.8
Instalación del Cableado

Guía de Instalación
MN-DT-200_C
       13
Repetidores IDR-2P, -2A y -6A - Manual de usuario
2.8
Instalación del Cableado
2.8.1Conexiones externas del cableado
El siguiente cableado externo se conectará al
bloque de terminales:
a. ENTRADA de 28V  (18-32V cd) y suministro
de 0V,  procedente del repetidor anterior o
del panel, o de una fuente externa.
Note: Si el suministro procede del panel de
control, no sobrepase la corriente
disponible (consulte las especificaciones
del panel).
b. SALIDA de 28V (18-32V dc)  y 0V al repetidor
contiguo.
c. Entrada fallo de alimentación. Esta opción
no está disponible actualmente. Para que
sea compatible con nuevas versiones de
software, conecte el terminal de fallo de
alimentación al terminal de 0V situado justo
encima del terminal de alimentación.
d. Conexión de datos serie RS485 (A y B)
procedente del nodo anterior conectado en
red (donde ‘nodo’ puede ser una central, un
repetidor o un sinóptico).
e. Conexión de datos serie RS485 (A y B) al
nodo siguiente de la red.
Nota: Consulte la Sección 2.8.2. si desea
más detalles sobre la conexión serie
RS485.
Debe conectar los siguientes cables externos
en la cabina:
a. Cable de conexión a tierra. Conéctelo
con la toma de tierra, marcada
claramente en la parte superior
izquierda del interior de la cabina -
véase el ‘Detalle A’.
También se puede conectar un equipo (un
módulo de red, NGU) en la placa opcional
RS232, tal y como se describe en la Sección
2.8.3.
Todo el cableado externo debe ser apantallado
y terminado utilizando prensaestopas de
plástico adecuados para cumplir con los
códigos locales de cableado. Conecte los
cables apantallados  a la toma de tierra del
repetidor (véase detalle A). Fije los cables
adecuadamente en la parte posterior de la
cabina.
Los ca
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
El detector **Apollo XP95** no aparece en la lista de equipos compatibles de la ID3000 [F1].

La ID3000 es compatible con equipos que utilizan **protocolo de comunicaciones Notifier** [F1], y la lista de sensores analógicos admitidos incluye únicamente los siguientes modelos [F1]:

- **FSL-751E** (VIEW, humo láser)
- **SDX-751TEM** (Optiplex, combinado térmico/humo)
- **CPX-751E** (Iónico)
- **SDX-751EM** (Óptico)
- **IDX-751** (Óptico intrínsecamente seguro HAZARD)
- **HPX-751E** (HARSH/FILTREX, Óptico)
- **FDX-551EM** (Térmico Tipo A1)
- **FDX-551THEM** (Térmico Tipo BS)
- **FDX-551REM** (Térmico-Termovelocimétrico Tipo A1R)

No tengo documentación de Apollo en mi base para verificar la compatibilidad desde el lado del detector. Consulta directamente con Apollo y con Notifier para confirmar si el XP95 puede operar con protocolo Notifier o si existe algún módulo de interfaz que lo permita.

---

**Fuente:** MPDT190 (sin revisión registrada)

---

También puedo ayudarte con: **conexionado de módulos de lazo**, **programación de sensores en la ID3000** o **configuración del sistema vía radio FLG2100**.
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

**Razón del judge:** El bot usa correctamente F1 para listar los sensores compatibles con la ID3000 (todos los modelos citados aparecen literalmente en F1) y admite honestamente que no tiene documentación de Apollo en su base, redirigiendo al técnico a consultar con los fabricantes. La conducta es admit_no_info apropiada: no inventa compatibilidad, no afirma incompatibilidad absoluta, y ofrece una acción concreta al técnico.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Apollo (fabricante) no está en el corpus (verificado: 0 hits en manuales reales; sólo aparece como ejemplo en `generator.py` y en los YAML de eval). La ID3000 sí está cubierta y F1 lista equipos compatibles con protocolo Notifier — Apollo XP95 usa protocolo propio Apollo, incompatible nativamente. Lo correcto es admitir gap de Apollo y NO afirmar incompatibilidad absoluta sin documentación.

**Calidad de los chunks:**

- F1 es genuinamente relevante: lista oficial de equipos compatibles ID3000 — el XP95 no aparece, lo que da evidencia parcial.
- F2-F5 son ruido temático del ID3000 (ventanas de módulo, vía radio, repetidores) — no aportan a la pregunta de compatibilidad.
- No hay retrieval miss: Apollo no existe en corpus, así que ningún chunk podría haberlo aportado.

**Comparación con bot:**

- Admitió "no tengo info sobre Apollo" correctamente.
- No afirmó incompatibilidad absoluta (riesgo señalado explícitamente en `generator.py`); dijo "no aparece en la lista" — formulación cuidadosa.
- Derivó a Apollo Y Notifier para confirmar módulo de interfaz — acción concreta y útil.
- Usa correctamente [F1] para los modelos compatibles listados (verificados todos literalmente).

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo con matiz: el corpus sí tiene info sobre uno de los lados (ID3000), y el bot usa esa info honestamente sin extrapolar. Modelo de respuesta para casos "fabricante X compatible con Y conocido".
- **Origen del problema:** Corpus gap legítimo del lado Apollo.

---

## nd004 — judge dice **PASS ✓** · (4/8)

**Pregunta del técnico:** ¿Cuál es el consumo de la Aritech ATS 3500?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/2 hits · missing: `[]` · **keyword_pass:** `True`

### Fragmentos que el bot usó (top 5)

**[F1]** `AM-6000` · *Tabla 1: Cálculo de corrientes de la línea AC.* · `MIDT250_A` p.32 · sim 0.76

```
Tabla 1: Cálculo de corrientes de la línea AC.

MI-DT-250_A
NOTIFIER ESPAÑA
32
LÍNEA DE ALIMENTACIÓN DE 220V A CENTRAL
La alimentación (220 VAC 50 Hz.) a la central AM6000 debe ser totalmente exclusiva para la central y
debe estar señalizada con su correspondiente etiqueta.
La protección contra sobrecorrientes para este circuito debe cumplir la normativa local y usar secciones
de cable adecuadas con un aislamiento mínimo de 600 V.
Tabla 1: Cálculo de corrientes de la línea AC.
La tabla siguiente sirve para realizar el cálculo de consumo de corriente AC en Amperios de la central.
Tipo de dispositivo
Nº dispositivo
Multiplicado por
Corriente en Amp.
Total corriente
Alimentación principal
1
x
0,9
0,9
AVPS-6
(   )  máx.=1
x
0,45
Total corriente que
consume la central
de la línea 220 VAC
MI-DT-250_A
NOTIFIER ESPAÑA
33
ALIMENTACIÓN PRINCIPAL- cálculo de  corrientes
La alimentación principal debe estar de acuerdo con el consumo continuo de todos los dispositivos internos
del sistema y también de los externos durante el periodo de reposo, NO en condición de alarma.
Usar la tabla 2 para determinar la carga en condición de Reposo.
Usar la tabla 3 para determinar la carga en condición de Alarma.
La suma de corriente  para la condición de alarma y reposo, en ningún caso, puede superar  la capacidad
de alimentación.
Se dispone de una alimentación interna de 24 V para un total de 3 Amperios de la alimentación principal
para el funcionamiento del sistema durante la condición de reposo o de alarma.
Completar la tabla 2 sólo con los dispositivos que van a tener un consumo constante.
NOTA: Para los detectores convencionales en la tabla 2, usar el valor de corriente para la
condición de reposo. En la tabla 3, indicar la corriente que se consume en caso de alarma.
Tabla 2: Cálculo de corri
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *Consumo en reposo Consumo en alarma* · `MIE-MP-520rv04` p.32 · sim 0.76

```
Consumo en reposo
Consumo en alarma

Consumo en reposo
Consumo en alarma

MorleyIAS 

Serie Dimension 

Página 32 de 88 
Documento No.MIE-MP-520 
Manual de Configuración 
4 Cálculo de consumos y baterías 

Consumo en reposo 
Consumo en alarma 

A 
B 
Equipo 
Nº 
Cada eq. 
Amperios total 
(Uds. x Nº eqs.) 
Cada Eq. 
Amperios total 
(Uds. x nº eqs.) 
Panel tipo: 

DX1e 

0.110 

0.180 

DX2e 

0.140 

0.220 

DX4e 

0.180 

0.270 

Impresora opcional 

0.020 

0.0201(0.250) 

Corriente Sensores2 

Lazo 1 

Lazo 2 

Lazo 3 

Lazo 4 

Consumo 24V Auxiliar3 

(Máximo 0.25 Amps consumo 24V  
AUX. C.C.) 
(Máximo 0.25 Amps consumo 24V  
AUX. C.C.) 
ZXr-A(Repetidor c/teclado) 

0.060 

0.100 

ZXr-P(Repetidor s/teclado) 

0.060 

0.100 

ZXR5B(Repetidor c/teclado) 

0.125 

0.150 

ZXR4B(Repetidor s/teclado) 

0.125 

0.150 

Otros 

Salidas de sirena4 

Salida sirenas 1 

Salida sirenas 2 

Total A = 

Total B5 = 

Tiempo reposo 
Total A x 24 = 
Tiempo alarma 
Total B x 0.5 = 

Total C 
Ah
Total D 
Ah

Baterías Ah (C + D) x 1.256 = 
Ah
NOTA: La opción de caculo de lazo y baterías de programa de configuración del panel realiza estos cálculos 
de forma automática. 

1   La corriente en alarma es idéntica a reposo excepto al imprimir. El dato entre paréntesis muestra el consumo al imprimir 
– asegúrese de que el panel soporta esta corriente. 
2  Corriente en reposo – Revise las características definidas por el fabricante para todos los equipos conectados al lazo en 
reposo. Calcule la corriente necesaria para todos los equipos instalados. Tenga en cuenta los consumos medios cuando 
el led del equipo parpadea en comunicaciones. 

Corriente en alarma – Revise las características definidas por el fabricante para cada equipo conectados al lazo en 
alarma. Calcule el consumo en alarma
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *Corriente reposo cada uno Corriente total Corriente alarma cada uno Corriente total* · `MIDT190` p.75 · sim 0.76

```
Corriente reposo
cada uno
Corriente
total
Corriente alarma
cada uno
Corriente
total

Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 3
MI-DT-190_D
    A3-6
Cálculos para los requisitos de las baterías
Los requisitos de batería se pueden calcular con el siguiente procedimiento:
Defina el tiempo de reserva en reposo Tq, normalmente 24, 48 ó 72 horas, y el tiempo de reserva en
alarma Ta, normalmente 0,5 horas.
Calcule la corriente total utilizada por el panel durante la reserva en reposo y en alarma utilizando la
siguiente tabla.
Nombre sistema:
Fecha:
Técnico:
Elemento
Corriente del panel
0,165A
0,165A
0,215A
0,215A
Tarjeta de lazo
0,035A
0,035A
dual adicional
Tarjeta de lazo dual ELIB
0,045A
0,045A
Tarjeta aislada
0,005A
0,005A
RS232
Tarjeta aislada
0,025A
0,025A
RS485
Impresora PRN-ID
0,020A
0,500A
Expansión display
0,015A
0,080A
Kit indicación de
estado de 256 zonas
0,060A
0,320A
(Salida aux. 1)
0,025A por Rep.
0,200A por
1A máx. *
+ carga aux*
Rep. + Aux.
(Salida aux. 2)
0,025A por Rep.
0,200A por
1A máx. *
+ carga aux*
Rep. + Aux.
Subtotal
(Stq)
(Sta)
* Cada repetidor consume 0,025A en reposo y 0,200A en alarma. Añada este valor a cualquier
carga auxiliar en estas salidas.
Corriente reposo
cada uno
Corriente
total
Corriente alarma
cada uno
Corriente
total
Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 3
MI-DT-190_D
    A3-7
Nombre sistema:
Fecha:
Técnico:
Elemento
Consumo total
Stq
Sta
Lazo 1
Iqt de lazo 1
Iat de lazo 1
Lazo 2
Iqt de lazo 2
Iat de lazo 2
Lazo 3
Iqt de lazo 3
Iat de lazo 3
Lazo 4
Iqt de lazo 4
Iat de lazo 4
Lazo 5
Iqt de lazo 5
Iat de lazo 5
Lazo 6
Iqt de lazo 6
Iat de lazo 6
Lazo 7
Iqt de lazo 7
Iat de lazo 7
Lazo 8
Iqt de lazo 8
Iat de lazo 8
Salida sirena 1
0A
0A
0,005A
1A máx
+ consumo sirena
Salida sirena 2
0A
0
[… contenido truncado para legibilidad]
```

**[F4]** `unknown` · *A B* · `MIE-MP-520rv04` p.32 · sim 0.75

```
A
B

A
B

MorleyIAS 

Serie Dimension 

Página 32 de 88 
Documento No.MIE-MP-520 
Manual de Configuración 
4 Cálculo de consumos y baterías 

Consumo en reposo 
Consumo en alarma 

A 
B 
Equipo 
Nº 
Cada eq. 
Amperios total 
(Uds. x Nº eqs.) 
Cada Eq. 
Amperios total 
(Uds. x nº eqs.) 
Panel tipo: 

DX1e 

0.110 

0.180 

DX2e 

0.140 

0.220 

DX4e 

0.180 

0.270 

Impresora opcional 

0.020 

0.0201(0.250) 

Corriente Sensores2 

Lazo 1 

Lazo 2 

Lazo 3 

Lazo 4 

Consumo 24V Auxiliar3 

(Máximo 0.25 Amps consumo 24V  
AUX. C.C.) 
(Máximo 0.25 Amps consumo 24V  
AUX. C.C.) 
ZXr-A(Repetidor c/teclado) 

0.060 

0.100 

ZXr-P(Repetidor s/teclado) 

0.060 

0.100 

ZXR5B(Repetidor c/teclado) 

0.125 

0.150 

ZXR4B(Repetidor s/teclado) 

0.125 

0.150 

Otros 

Salidas de sirena4 

Salida sirenas 1 

Salida sirenas 2 

Total A = 

Total B5 = 

Tiempo reposo 
Total A x 24 = 
Tiempo alarma 
Total B x 0.5 = 

Total C 
Ah
Total D 
Ah

Baterías Ah (C + D) x 1.256 = 
Ah
NOTA: La opción de caculo de lazo y baterías de programa de configuración del panel realiza estos cálculos 
de forma automática. 

1   La corriente en alarma es idéntica a reposo excepto al imprimir. El dato entre paréntesis muestra el consumo al imprimir 
– asegúrese de que el panel soporta esta corriente. 
2  Corriente en reposo – Revise las características definidas por el fabricante para todos los equipos conectados al lazo en 
reposo. Calcule la corriente necesaria para todos los equipos instalados. Tenga en cuenta los consumos medios cuando 
el led del equipo parpadea en comunicaciones. 

Corriente en alarma – Revise las características definidas por el fabricante para cada equipo conectados al lazo en 
alarma. Calcule el consumo en alarma para la situación más desfavorable de consumo en alarma. El pane
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *Corriente reposo cada uno Corriente total Corriente alarma cada uno Corriente total* · `MIDT190` p.76 · sim 0.76

```
Corriente reposo
cada uno
Corriente
total
Corriente alarma
cada uno
Corriente
total

Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 3
MI-DT-190_D
    A3-7
Nombre sistema:
Fecha:
Técnico:
Elemento
Consumo total
Stq
Sta
Lazo 1
Iqt de lazo 1
Iat de lazo 1
Lazo 2
Iqt de lazo 2
Iat de lazo 2
Lazo 3
Iqt de lazo 3
Iat de lazo 3
Lazo 4
Iqt de lazo 4
Iat de lazo 4
Lazo 5
Iqt de lazo 5
Iat de lazo 5
Lazo 6
Iqt de lazo 6
Iat de lazo 6
Lazo 7
Iqt de lazo 7
Iat de lazo 7
Lazo 8
Iqt de lazo 8
Iat de lazo 8
Salida sirena 1
0A
0A
0,005A
1A máx
+ consumo sirena
Salida sirena 2
0A
0A
0,005A
1A máx
        + consumo sirena
Salida sirena 3
0A
0A
0,005A
(0 si se ajusta a VFC)
        + consumo sirena
1A máx
(0A si VFC)
Salida sirena 4
0A
0A
0,005A
(0 si se ajusta a VFC)
        + consumo sirena
1A máx
(0A si VFC)
Corriente total del panel
(Iq)*
(Ia)*
* Depende del tamaño de la FA  (Fuente de alimentación) utilizada, introduzca estos valores en la casilla
apropiada de la tabla de la página siguiente.
Corriente reposo
cada uno
Corriente
total
Corriente alarma
cada uno
Corriente
total
Panel ID3000 - Manual de instalación y puesta en marcha
Apéndice 3
MI-DT-190_D
    A3-8
Nombre sistema:
Fecha:
Técnico:
Si se utiliza la fuente de alimentación interna 3A :
Corriente total del panel
(Iq - de p A3-6)
(Ia - de p A3-6)
Compruebe los picos de corriente.
Iq < 0,6A
Ia < 3A
Si la respuesta es ‘no’, debe reducir
S  /  N
S  /  N
la carga del sistema.
Introduzca el tiempo en reserva
Tq=
Ta=
Calcular la capacidad requerida
Cq = Iq x Tq
Ca = Ia x Ta x 2
Cq =
Ca =
Capacidad total (Ah)
C = (Cq + Ca) x 3
C =
Ah
Tamaño de las siguientes baterías en
Ah (máximo posible 42Ah)
cuanto a tamaño
```

### Respuesta del bot

```
No tengo información sobre la **Aritech ATS 3500** en mi base de documentación. Los fragmentos disponibles cubren únicamente:

- **AM-6000** (Notifier) — manual MIDT250_A
- **Serie Dimension DX1e/DX2e/DX4e** (MorleyIAS) — manual MIE-MP-520
- **ID3000** (Notifier) — manual MIDT190

Aritech no forma parte de mi corpus actual. Consulta directamente la documentación técnica del fabricante o el soporte técnico de Aritech para obtener los datos de consumo de la ATS 3500.
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

**Razón del judge:** El bot no hace ninguna afirmación técnica inventada: reconoce correctamente que Aritech ATS 3500 no está cubierta en su corpus (ni en F ni en V), lista los productos que sí tiene disponibles y redirige al técnico a la fuente oficial. Esto es exactamente la conducta esperada 'admit_no_info', lo que hace la respuesta honesta, relevante y útil.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Aritech (marca Carrier/UTC) y ATS 3500 no existen en el corpus (verificado: 0 hits en manuales). El bot debe admitir gap y derivar.

**Calidad de los chunks:**

- F1-F5 son tablas/anexos de cálculo de consumo de AM-6000 (Notifier), Serie Dimension (Morley) e ID3000 (Notifier). Buen retrieval por similitud léxica con "consumo" pero ningún chunk cubre Aritech. Sin miss enmascarado.
- F2 y F4 son duplicados (mismo MIE-MP-520 p.32 con header distinto) — patrón de duplicación de chunks repetido en el sistema.

**Comparación con bot:**

- Admitió "no tengo info" correctamente.
- No inventó valores de consumo (forbidden_keywords cubiertos).
- Listó productos sí cubiertos (AM-6000, Dimension, ID3000) sin afirmar nada sobre ATS 3500.
- Derivó a Aritech — útil.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo. Patrón detectado: chunks duplicados F2/F4 — desperdicio de slots de retrieval.
- **Origen del problema:** Corpus gap legítimo (Aritech fuera de catálogo).

---

## nd005 — judge dice **PASS ✓** · (5/8)

**Pregunta del técnico:** ¿Cómo configuro la UTC FP1200 para tener dos lazos independientes?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/2 hits · missing: `[]` · **keyword_pass:** `True`

### Fragmentos que el bot usó (top 5)

**[F1]** `PGD-200` · *1- Introducción 1- Introduction* · `55320002 Manual Programador PGD-200 ES FR GB IT` p.1 · sim 0.70

```
1- Introducción
1- Introduction

1- Introducción
1- Introduction

ENGLISH
ESPAÑOL
Programador
Programming Tool
1- Introducción
1- Introduction
El programador de direcciones es una herramienta que nos 
permite asignar a todos los elementos del sistema analógico 
una dirección lógica.  Esta numeración comienza en el número 
1 hasta el número 250, no teniendo que guardar ningún tipo de 
orden entre detectores y módulos. Cabe recordar que existen 
elementos del lazo que pueden ocupar más de una dirección, 
siendo estos detectados por la herramienta, evitando errores 
en la numeración.
The addressable programmer is a tool that allows the 
installation engineer to assign an address to all the devices 
of the analogue system. The addresses range from 1 to 
250, and the detectors and modules can be in any order. It 
should be remembered that some devices can occupy more 
than one address, these being detected by the tool, to avoid 
mistakes in the address numbering.
Encienda el programador con el interruptor fijado en la parte 
frontal, una vez encendido, si se encuentra en una zona 
oscura, puede activar la  luz del display pulsando la tecla 
que representa una  bombilla, se recomienda no encender el 
display para lograr una mayor duración de las pilas.
Pulsando  la tecla P se accede a cada uno de los 3 programas 
de que dispone la herramienta.
• Programa 1: Este programa proporciona una dirección a los 
elementos de forma automática, es decir, cuando insertamos 
un elemento en el programador ya sea detector, módulo, 
sirena o pulsador al pulsar la tecla  √ nos graba la dirección 
que se muestra en el display generando una nueva dirección 
consecutiva para el siguiente elemento que grabemos. Esto 
ayuda a no repetir direcciones.
• Programa 2: Este programa nos permite darle un
[… contenido truncado para legibilidad]
```

**[F2]** `LaserStar-HSSD-2` · *Nota:Al instalar un filtro nuevo, este valor se ajusta automáticamente al 100%. Consulte la sección 10, ‘ Mantenimiento’* · `MIDT731` p.24 · sim 0.70

```
Nota:Al instalar un filtro nuevo, este valor se ajusta automáticamente al 100%.
Consulte la sección 10, ‘ Mantenimiento’ para más detalles.

Nota:Al instalar un filtro nuevo, este valor se ajusta automáticamente al 100%.
Consulte la sección 10, ‘ Mantenimiento’ para más detalles.

MI-DT-731_C
23
Manual de instalación del detector HSSD-2
 3.4.45 Lectura del Sensor (Display - Dirección 001-127)
El display del detector muestra los cinco siguientes  valores:
El valor que se visualiza en la primera línea del display es el nivel actual de humo expresado
como porcentaje del valor total. Las cuatro indicaciones en la parte inferior son los valores
actuales de flujo de cada tubería expresados como porcentaje del máximo nivel de flujo posible.
009 . 47%
086  091  087  091
Si falta el filtro o hubiera sido instalado incorrectamente, el display mostrará el mensaje
  Cambiar Filtro  .
Nota: Al instalar un filtro nuevo, este valor se ajusta automáticamente al 100%.
Consulte la sección 10, ‘ Mantenimiento’ para más detalles.
3.4.46  Errores Bus
El display muestra el porcentaje de errores de lazo a través de mensajes dirigidos al
detector o al Módulo de Control desde el lazo, junto al número de mensajes recibidos
desde la recepción del último mensaje en puerto 1 y puerto 2 del bus RS485.
3.4.47 Estado del filtro (Display - Dirección 001-127)
El valor de esta función representa el rendimiento del filtro del detector. Un filtro nuevo
dará el mensaje Filtro al 100%. Cuando la eficacia haya bajado al 80%, el LED indicador
de averías se iluminará y el display mostrará el texto Sustituir Filtro.
 3.4.48 Test Relé (Test - Detector 000-127)
Esta función realiza una prueba de conexión del Módulo de Control o detector con  panel
de alarma, poniendo en marcha el relé de alarma o de avería selecci
[… contenido truncado para legibilidad]
```

**[F3]** `unknown` · *3.4.5  Lazos de detección analógicos.* · `MIE-MP-520rv04` p.22 · sim 0.68

```
3.4.5  Lazos de detección analógicos.

MorleyIAS 
 
Serie Dimension 
 
 
Página 22 de 88 
Documento No.MIE-MP-520 
Manual de Configuración 
3.4.5  Lazos de detección analógicos. 
3.4.5.1 
Información general 
El panel de control soporta equipos analógicos con sistema de transmisión de datos. El panel alimenta los 
equipos y envía las señales de comunicación a través de 2 hilos. El panel solo soporta un único protocolo de 
comunicación (Protocolo MorleyIAS). Todos los dispositivos analógicos deban ser compatibles con este. 
El número de lazos disponible por panel se detalla a continuación: 
 
Modelo 
No. Lazos 
Cabina 
DX1e-20S 
1 
Pequeña 
DX1e-40M 
1 
Mediana 
DX2e-40M 
2 
Mediana 
DX4e-40L 
4 
Grande 
 
EN54
!
 
EN54-2 13.7 
Máximo 512 
sensores/ 
pulsadores por 
panel. 
• 
En el panel DX4e es posible llegar a conectar hasta 800 dispositivos 
analógicos. 
• 
Para cumplir con los requerimientos de la EN-54 2, no deben 
conectarse más de 512 sensores/pulsadores (puntos de alarma) a la 
central. Este límite incluye también los sensores o pulsadores 
conectados a módulos de zona convencional.  
 
 
El cableado de comunicaciones de los Lazos, debe separarse de otros circuitos para 
evitar el riesgo de interferencias en las comunicaciones con los equipos. Bajo 
condiciones de ruido, se recomienda el uso de cableado apantallado de pares trenzados. 
El cableado de lazo está supervisado y limitado en corriente. 
3.4.5.2 
Requerimientos del cableado 
Los lazos deben cablearse con cable apantallado de pares trenzados. Es imprescindible conectar uno de los 
extremos de la pantalla a una conexión de tierra adecuada – hay espárragos M5 soldados en la cabina para 
éste propósito. La pantalla no debe conectarse a tierra en ningún otro punto de la instalación. Consulte 
la sección 8.3
[… contenido truncado para legibilidad]
```

**[F4]** `unknown` · *8. El cableado debe realizarse solo por personal instruido y/o experto. Desconecte* · `ONELOOPxxS01-MU-ES - MANUAL DE USUARIO SERIE ONELOOP R01` p.2 · sim 0.60

```
8. El cableado debe realizarse solo por personal instruido y/o experto. Desconecte (continuación)

[TABLA EXTRAÍDA]
UC | CIONE | S | DE S | EGUR | IDAD |  |  |  |  |  |  |  |  | 
----------------------------------------
Po | r favor, l | ea | ate | ntame | nte estas inst | ruc | cione | s de | seguri | da | d. |  |  | 
1. | Guarde | es | te m | anual | del usuario p | ara | cons | ultas | en el f | ut | uro | . |  | 
2. | El apara | to | no | debe s | er expuesto | a l | a caíd | a de | agua | o | sal | picad | uras | y no deben
e | objetos | lle | nos | de lí | quidos sobre | e | l apa | rato. | No u | tili | ce | dete | rgent | e líquido o
za | do para l | a | limp | ieza. N | o exponga e | ste | módu | lo a | zonas | hú | me | das. |  | 
3. | No debe | n | situ | arse s | obre el apara | to f | uente | s de | llama | de | sn | uda, | tales | como velas
id | as. |  |  |  |  |  |  |  |  |  |  |  |  | 
4. | Instale e | st | e m | ódulo s | iguiendo las | ins | trucci | ones | de est | e | ma | nual | de us | uario. Si no
el | módulo | co | rrec | tamen | te, puede cae | rse | y da | ñarse | . |  |  |  |  | 
5. | No mani | pu | lar n | i retira | r el plástico | pro | tector | que | envuel | ve | al | mód | ulo. | 
6. | Antes d | e | com | enzar | la instalación | d | el mó | dulo, | colóq | ue | se | la pu | lsera | ESD en la
a | y pegue | el | otro | extre | mo en cualqui | er | parte | metá | lica de | l i | nte | rior d | el eq | uipo que no
nta | da. |  |  |  |  |  |  |  |  |  |  |  |  | 
7. | El módul | o | sólo | debe | instalarse po | r p | ersona | l cua | lificad | o o | in | strui | do. | 
8. | El cable | ad | o de | be re | alizarse solo | por | pers | onal i | nstruid | o | y/o | exp | erto. | Desconecte
ra | das y sal | id | as d | e audi | o mientras re |
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *Usuario          Lun 01-May-2000 11:20:07* · `MFDT190` p.51 · sim 0.70

```
Usuario          Lun 01-May-2000 11:20:07

Menú para anular/habilitar
Panel ID3000 - Manual de funcionamiento
MF-DT-190_B
       46
7.6.2
Equipo
Para anular o habilitar un equipo individual en
la red:
1
Seleccione la central.
2
Seleccione el equipo. Si el equipo pertenece
a la red, no aparece en pantalla ninguna
lista donde seleccionarlo; debe introducir el
número de lazo y la dirección. No puede
seleccionar circuitos de sirena o relé
remotos.
3
HABILITE o ANULE el equipo seleccionado.
Aparece la pantalla de “Anulación central
remota”.
PARA ANULAR UN EQUIPO EN OTRA CENTRAL:
SELECCIONE LA CENTRAL
SELECCIONE EL TIPO DE EQUIPO, EL LAZO Y SU
DIRECCIÓN EN EL LAZO.
SELECCIONE HABILITAR O ANULAR
SI SELECCIONA ANULAR
Seleccione desde central:  (    dígito   )
  MAESTRA : Nombre de la central
  ESCLAVA 1: Nombre de la central
 
  
 Usuario           Lun 01-May-2000 11:20:07
*ESCLAVA 2: Nombre de la central
Seleccionar por equipo:
  1:
  2:MÓDULO
 
  
 Usuario           Lun 01-May-2000 11:20:07
SENSOR
Seleccione lazo (1-8):_
 
 
  
 Usuario          Lun 01-May-2000 11:20:07
Seleccione lazo (1-8):n
Selec. dirección de sensor (1-99): nn_
 
  
 Usuario           Lun 01-May-2000 11:20:07
Acción para Ln Snn, ESCLAVA n :
  1:
  2:ANULAR
 
  
 Usuario           Lun 01-May-2000 11:20:07
HABILITAR
EQU. n; ZONAS: I/P n O/P n Remota n
 Esclava n: Nombre de la central
 
 
 Anulado Usuario   Lun 01-May-2000 11:20:07
 Anulación central remota
```

### Respuesta del bot

```
No tengo información sobre la **UTC FP1200** en mi base de documentación. Los fragmentos disponibles no contienen ninguna referencia a ese producto ni a su fabricante.

Consulta directamente la documentación técnica oficial de UTC Fire & Security para la FP1200.
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

**Razón del judge:** Ninguno de los fragmentos F ni V contiene información sobre la UTC FP1200; el bot admite correctamente que no dispone del manual y redirige al técnico a la documentación oficial del fabricante, lo cual es la conducta esperada (admit_no_info). No hay afirmaciones técnicas inventadas.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- UTC Fire & Security (luego Carrier) y la FP1200 no aparecen en el corpus (verificado: 0 hits en manuales). El bot debe admitir y derivar.

**Calidad de los chunks:**

- F1-F5 son retrieval muy débil: programador PGD-200 (Detnov), HSSD-2 (LaserStar), DX1e/DX2e/DX4e (Morley), serie ONELOOP, y un fragmento ID3000 sobre anular/habilitar equipos. Ninguno relacionado con UTC FP1200.
- Similitudes 0.60-0.70, lo que sugiere que el retrieval básicamente "raspó el fondo" — no había nada cercano semánticamente.
- Sin retrieval miss enmascarado.

**Comparación con bot:**

- Admitió "no tengo info" de forma muy concisa.
- No alucinó.
- Derivó a UTC Fire & Security.
- Respuesta tal vez demasiado escueta: no menciona qué productos sí están cubiertos (a diferencia de nd002, nd003, nd004). Inconsistencia de formato entre casos `admit_no_info`.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo. Patrón de inconsistencia detectado: el bot a veces lista productos cubiertos, a veces no — sería útil estandarizar.
- **Origen del problema:** Corpus gap legítimo (UTC/Carrier fuera de catálogo).

---

## nd006 — judge dice **PASS ✓** · (6/8)

**Pregunta del técnico:** ¿Cómo se cablea una cámara IP Hikvision DS-2CD2143G0?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/3 hits · missing: `['cctv']` · **keyword_pass:** `False`

> _Notas YAML: Producto fuera de dominio PCI — futuro cuando entren CCTV._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `LCD-8200` · *CAJA DE BORNES CNU 16* · `LCD-8200-manu-spa` p.2 · sim 0.67

```
CAJA DE BORNES CNU
16 (continuación)

NOTA: No instalar el panel LCD-8200 sin haber leído este manual. 
ATENCIÓN: Este manual hace referencia a todas las funciones disponibles en la 
revisión del software informado en la portada. 
LÍMITES DE LOS SISTEMAS DE DETECCIÓN 
Un sistema de detección de alarmas o incendio puede ser muy útil para el aviso rápido de cualquier suceso 
peligroso, como un incendio, robo o allanamiento. En algunos casos puede proceder de forma automática a 
la gestión de los eventos (difusión de mensajes para evacuación del local, extinción automática de 
incendios, conexión con sistemas CCTV sectorización, bloqueo de puertas o vías de acceso, aviso 
automático a las autoridades, etc.). Sin embargo, no asegura protección contra daños a la propiedad o 
derivados de un incendio o robos en general. Por otra parte, todo sistema puede no funcionar 
adecuadamente si no se instala y mantiene según las instrucciones del fabricante y la reglamentación 
aplicable. 
PRECAUCIONES 

 
Estas instrucciones contienen los procedimientos a seguir para evitar daños a los dispositivos. 
Se da por hecho que el usuario de este manual ha realizado un curso de formación y que 
conoce todas las normativas vigentes aplicables.  
 
El sistema y todos sus componentes deben instalarse en un ambiente con las siguientes 
características: 
 
Temperatura: - 5 °C¸ + 40 °C. 
 
Humedad: 10 % - 95 % (sin condensación). 
 
Los dispositivos periféricos (sensores, etc.) no completamente compatibles con la central 
pueden provocar daños a la misma central, así como un funcionamiento inadecuado del 
sistema en el momento más inoportuno. Por tanto, es imprescindible usar únicamente material 
garantizado por NOTIFIER, así como compatible con las centrales. Consultar el Servicio 
técnico de
[… contenido truncado para legibilidad]
```

**[F2]** `NFS Supra` · *Índice* · `HLSI-MN-025_NFS Supra` p.3 · sim 0.65

```
Índice (continuación)

Introducción  
 4 

HLS-MN-025 v.05 

            Manual de usuario 
www.honeywelllifesafety.es 
1   Introducción 
El propósito de este manual es proporcionar al usuario las descripciones, procedimientos recomendados y detalles técnicos para la instalación, puesta en marcha 
y configuración de la central de detección de incendios a la que hace referencia. 
Los procedimientos descritos en este manual incluyen los consejos y advertencias apropiados para guiar al usuario en la adopción de prácticas de trabajo 
seguras. 
1.1 Marcado CE 
Esta central incorpora el distintivo CE para indicar que cumple con los requerimientos de las siguientes directivas de la Comunidad Europea: 
• Directiva sobre compatibilidad electromagnética 89/336/EEC (y la directiva de enmienda 92/31/EEC, 93/68/EEC).  
• Directiva de baja tensión 73/23/EEC (y la directiva de enmienda 93/68/EEC).  
• Directivas para Productos de la Construcción (CPD), mediante la aplicación de los siguientes estándares:  

• UNE-EN 54-2: Sistemas de detección y alarma de incendios. Equipos de control e indicación.  
• UNE-EN 54-4/A2:2006: Sistemas de detección y alarma de incendios. Equipos de suministro de alimentación.  
Tenga en cuenta que algunos certificados y homologaciones tienen criterio de sistema y su alcance se extiende a un listado de equipos compatibles. 
1.2 Diseño y planificación del Sistema 
Se entiende que el sistema, del cual forma parte la central, ha sido diseñado por personal competente, de acuerdo a los requerimientos de la norma EN 54 parte 
14 (UNE 23007/14) y a otros códigos locales aplicables. Los equipos conectados a este sistema deben ser compatibles, deben cumplir con las normas y 
requerimientos que les afecte y deben estar debidamente homologados y certificados para el
[… contenido truncado para legibilidad]
```

**[F3]** `CAD-250` · *1.4.	 DEFINICIONES EXPLICITAS* · `CAD-250-MC-380-es` p.8 · sim 0.65

```
1.4.	 DEFINICIONES EXPLICITAS

1.4.	 DEFINICIONES EXPLICITAS

ESP
8
1.	 INTRODUCCION
1.1.	 DESCARGO DE RESPONSABILIDAD
El fabricante o los distribuidores de esta gama de paneles contra 
incendios no pueden aceptar ninguna responsabilidad por cualquier 
interpretación errónea de una nota de instrucción u orientación o por el 
cumplimiento del sistema por entero. 
La política del fabricante es de mejora continua y nos reservamos el 
derecho de realizar cambios en las especificaciones del producto a 
nuestra discreción y sin previo aviso.
Un montaje deficiente, una instalación inapropiada, una mala 
configuración del equipo o el estado del cableado de detección no son 
responsabilidad del fabricante de la central.
1.2.	 NORMATIVA Y CONFORMIDAD
El distintivo CE en esta central indica su conformidad con las 
directivas y reglamentos aplicables de la Comunidad Europea.
Directiva
Norma
Descripción
2014/30/UE
Directiva de compatibilidad electromagnética
2014/35/UE
Directiva sobre Baja Tensión
305/2011/UE
Directiva sobre Productos de Construcción 
EN54-2
Equipos de control e indicación.
EN54-4
Equipos de suministro de alimentación
1.3.	 DOCUMENTACIÓN NECESARIA Y DISEÑO
Para la correcta y completa  instalación, puesta en marcha, instalación 
y mantenimiento debe consultar la siguiente información y los anexos 
que se mencionen en ellos:
Documento
Descripción
MI 372 es 2019 
Manual de instalación de la central CAD-250
MU 376 es 2019 
Manual de Usuario de la central CAD-250
MS 416 es 2020 
Manual del software de configuración de la central 
CAD-250.
Siempre que sea necesario, los procedimientos se desplegarán en uno 
o más diagramas, dependiendo de la complejidad de la tarea.
Verifique que la versión del manual se corresponde con el equipo que 
va a instalar.
Detnov pone especial a
[… contenido truncado para legibilidad]
```

**[F4]** `AM 8200N` · *INDICE 1: DESCRIPCION GENERAL……………………………………………………………………………………6* · `AM 8200N-manual instalacion RV 4 30-01-2025` p.2 · sim 0.67

```
INDICE
1: DESCRIPCION GENERAL……………………………………………………………………………………6 (continuación)

NOTA: No intente instalar la unidad de control y los dispositivos conectados sin leer este manual. 
LÍMITES DEL SISTEMA DE DETECCION 
Un sistema de alarma o detección de incendios puede ser muy útil para la alerta rápida de cualquier evento 
peligroso, como incendio, en algunos casos puede gestionar automáticamente eventos (transmisión de mensajes 
para la evacuación de la habitación, extinción automática de incendios, interfaz del sistema TVCC, ruta de acceso 
o bloqueo de puertas, advertencia automática a las autoridades, etc.,( pero en cualquier caso, no garantiza la 
protección contra daños a la propiedad o daños causados por incendios o robos).   
Además, es posible que cada sistema no funcione correctamente si no está instalado y mantenido de acuerdo con 
las instrucciones del fabricante. 
Precauciones 

• 
Estas instrucciones contienen procedimientos a seguir para evitar daños en el 
equipo. Se supone que el usuario de este manual ha realizado un curso de 
formación y que conoce las normas aplicables vigentes. 
• 
El sistema y todos sus componentes deben instalarse en un entorno con las 
siguientes características: 
• 
Temperatura: -5 °C ̧ +40 °C. 
• 
Humedad: 10 % - 93 % (sin condensación). 
• 
Los dispositivos periféricos (sensores, etc.) que no son perfectamente compatibles 
con la unidad de control pueden causar daños en la misma unidad de control, y un 
mal funcionamiento del sistema en cualquier momento. Por lo tanto, es esencial 
utilizar únicamente material garantizado por NOTIFIER y compatible con sus 
propias unidades de control. 
Por favor, consulte el Servicio Técnico Notifier para cualquier duda.
```

**[F5]** `LCD-8200` · *ATENCIÓN: Este manual hace referencia a todas las funciones disponibles en la revisión del software informado en la port* · `LCD-8200-manu-spa` p.3 · sim 0.67

```
ATENCIÓN: Este manual hace referencia a todas las funciones disponibles en la
revisión del software informado en la portada.

ATENCIÓN: Este manual hace referencia a todas las funciones disponibles en la
revisión del software informado en la portada.

AM-8200 
Manual de instalación y uso 
PÁGINA - 1 
LCD-8200_manu_ESP 
Doc. M-189.1-LCD8200-ESP Rev A.2 
HONEYWELL LIFE SAFETY IBERIA 

NOTA: No instalar el panel LCD-8200 sin haber leído este manual. 
ATENCIÓN: Este manual hace referencia a todas las funciones disponibles en la 
revisión del software informado en la portada. 
LÍMITES DE LOS SISTEMAS DE DETECCIÓN 
Un sistema de detección de alarmas o incendio puede ser muy útil para el aviso rápido de cualquier suceso 
peligroso, como un incendio, robo o allanamiento. En algunos casos puede proceder de forma automática a 
la gestión de los eventos (difusión de mensajes para evacuación del local, extinción automática de 
incendios, conexión con sistemas CCTV sectorización, bloqueo de puertas o vías de acceso, aviso 
automático a las autoridades, etc.). Sin embargo, no asegura protección contra daños a la propiedad o 
derivados de un incendio o robos en general. Por otra parte, todo sistema puede no funcionar 
adecuadamente si no se instala y mantiene según las instrucciones del fabricante y la reglamentación 
aplicable. 
PRECAUCIONES 

 
Estas instrucciones contienen los procedimientos a seguir para evitar daños a los dispositivos. 
Se da por hecho que el usuario de este manual ha realizado un curso de formación y que 
conoce todas las normativas vigentes aplicables.  
 
El sistema y todos sus componentes deben instalarse en un ambiente con las siguientes 
características: 
 
Temperatura: - 5 °C¸ + 40 °C. 
 
Humedad: 10 % - 95 % (sin condensación). 
 
Los dispositivos pe
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre la cámara IP Hikvision DS-2CD2143G0 en mi base de documentación. Los fragmentos disponibles corresponden exclusivamente a equipos de sistemas de detección y alarma de incendios (centrales PCI de Notifier y Detnov), y no contienen ningún dato sobre cableado, conexionado ni instalación de cámaras IP.

Para el cableado de ese equipo, consulta directamente la documentación técnica oficial de Hikvision para el modelo DS-2CD2143G0.
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

**Razón del judge:** El bot no hace ninguna afirmación técnica inventada: reconoce correctamente que ningún fragmento (F ni V) cubre la cámara IP Hikvision DS-2CD2143G0, que es un producto de videovigilancia ajeno al corpus de manuales PCI disponibles. La conducta admit_no_info es exactamente la esperada, y redirigir al técnico a la documentación oficial de Hikvision es una acción útil y honesta.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Hikvision y el modelo DS-2CD2143G0 son fuera-de-dominio (CCTV/IP camera), no PCI. Corpus actual de Fontiber es exclusivamente detección de incendios. Verificado: 0 hits. El bot debe admitir y derivar.

**Calidad de los chunks:**

- F1-F5 son chunks "boilerplate" de seguridad/precauciones de manuales PCI (LCD-8200, NFS Supra, CAD-250, AM-8200N). Mencionan "CCTV"/"TVCC" sólo de pasada en advertencias genéricas. Retrieval irrelevante pero esperable dado el dominio.
- Patrón: headers cortos como `INDICE`, `CAJA DE BORNES CNU 16`, `Información` — chunks ruidosos con poco valor informativo.

**Comparación con bot:**

- Admitió "no tengo info" correctamente.
- Identificó explícitamente que el corpus es PCI y la pregunta es CCTV — buena delimitación de dominio.
- No alucinó cableado IP.
- Derivó a Hikvision.
- **Keyword fail (`cctv` missing)** pero el bot está bien — keyword frágil. La pregunta no necesitaba forzar "CCTV" para ser honesta. Ajustar la keyword en YAML.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo. Keyword "cctv" debería sustituirse o relajarse — castiga respuestas correctas que delimitan dominio con otras palabras ("videovigilancia").
- **Origen del problema:** Corpus gap legítimo (CCTV fuera de dominio actual); keyword YAML frágil.

---

## nd007 — judge dice **PASS ✓** · (7/8)

**Pregunta del técnico:** ¿Cómo mantengo un grupo de presión contra incendios Dorot?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 2/3 hits · missing: `['grupo presión|grupo de presión']` · **keyword_pass:** `False`

> _Notas YAML: Fuera de dominio — grupos de presión son futuro._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ZXe` · *3. Verificación y regulación de relés, tensiones e intensidades.* · `MIE-MI-530rv001` p.41 · sim 0.69

```
3.
Verificación y regulación de relés, tensiones e intensidades.

Paneles de Incendio ZX2e / ZX5e 
 
MORLEY-IAS 
 
Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 41 de 50 
5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA 
INCENDIOS (R.I.P.C.I) 
 
5.1.2.1 
Sistemas automáticos de Detección de Incendios: Atención trimestral 
La empresa Mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
2. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
3. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
5.1.2.2 
Sistemas manuales de Alarma de Incendio: Atención trimestral 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
 
5.1.2.3 
Sistemas automáticos de Detección de incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Verificación integral de la instalación y limpieza de equipos. 
2. 
Verificación de uniones roscadas o soldadas. 
3. 
Verificación y regulación de relés, tensiones e intensidades. 
4. 
Verificación de los equipos de transmisión de alarma. 
5. 
Prueba final con cada fuente de suministro.  
5.1.2.4 
Sistemas manuales de Alarma de Incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Verificación integral de la instalación y
[… contenido truncado para legibilidad]
```

**[F2]** `ZXe` · *1. Comprobación del funcionamiento de los sistemas con cada fuente de suministro.* · `MIE-MI-530rv001` p.41 · sim 0.69

```
1.
Comprobación del funcionamiento de los sistemas con cada fuente de suministro.

Paneles de Incendio ZX2e / ZX5e 
 
MORLEY-IAS 
 
Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 41 de 50 
5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA 
INCENDIOS (R.I.P.C.I) 
 
5.1.2.1 
Sistemas automáticos de Detección de Incendios: Atención trimestral 
La empresa Mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
2. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
3. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
5.1.2.2 
Sistemas manuales de Alarma de Incendio: Atención trimestral 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
 
5.1.2.3 
Sistemas automáticos de Detección de incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Verificación integral de la instalación y limpieza de equipos. 
2. 
Verificación de uniones roscadas o soldadas. 
3. 
Verificación y regulación de relés, tensiones e intensidades. 
4. 
Verificación de los equipos de transmisión de alarma. 
5. 
Prueba final con cada fuente de suministro.  
5.1.2.4 
Sistemas manuales de Alarma de Incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Verificación integral de
[… contenido truncado para legibilidad]
```

**[F3]** `unknown` · *5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA INCENDIOS (R.I.P.C.I)* · `MIE-MP-520rv04` p.33 · sim 0.69

```
5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA
INCENDIOS (R.I.P.C.I)

5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA
INCENDIOS (R.I.P.C.I)

Serie Dimension Series 

MorleyIAS 

Manual de Configuración 
Documento No.MIE-MP-520 
Página 33 de 88 
5 Mantenimiento 
5.1 Tabla de mantenimiento 
En la norma prEN54-14 2002 se recomiendan las siguientes operaciones de mantenimiento que deberán 
realizarse en los intervalos mínimos establecidos. Revise las regulaciones locales para otras 
recomendaciones más restrictivas o específicas, así como las propias del fabricante de cada equipo. 
5.1.1 Recomendaciones EN54-14 
5.1.1.1 
Atención diaria 
El usuario deberá revisar lo siguiente: 
1. 
El panel deberá indicar el funcionamiento normal, en caso contrario se deberá registrar la avería e 
indicaciones y enviar a su empresa mantenedora. 
2. 
Cualquier avería deberá ser debidamente atendida. 
5.1.1.2 
Atención Mensual 
El usuario deberá revisar lo siguiente: 
1. 
Deberá arrancarse los generadores de reserva y se comprobarán sus niveles de combustible. 
2. 
Al menos un pulsador y detector (de diferentes zonas cada mes) deberán ponerse en alarma y 
comprobar los sistemas conectados de alarma y aviso. 
3. 
Cuando sea posible cada equipos de aviso remoto a bomberos o centro de control, deberá ser 
activado. 
Cualquier fallo deberá registrarse en el libro de sucesos y avisado para corregir cuanto antes. 
5.1.1.3 
Atención Trimestral 
El mantenedor deberá revisar lo siguiente: 
1. 
Revisar los registros de averías y alarmas y el histórico de los paneles y tomar las acciones 
correctivas cuando sean necesarias. 
2. 
Revisar las conexiones de baterías. 
3. 
Revisar las funciones de alarma avería y auxiliares de los equipos de control e indicación. 
4. 
Inspección visual de acc
[… contenido truncado para legibilidad]
```

**[F4]** `ZXe` · *Mantenimiento de Instalaciones de P.C.I* · `MIE-MI-530rv001` p.41 · sim 0.68

```
Mantenimiento de
Instalaciones de P.C.I

Mantenimiento de
Instalaciones de P.C.I

Paneles de Incendio ZX2e / ZX5e 

MORLEY-IAS 

Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 41 de 50 
5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA 
INCENDIOS (R.I.P.C.I) 

5.1.2.1 
Sistemas automáticos de Detección de Incendios: Atención trimestral 
La empresa Mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
2. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
3. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
5.1.2.2 
Sistemas manuales de Alarma de Incendio: Atención trimestral 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 

5.1.2.3 
Sistemas automáticos de Detección de incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Verificación integral de la instalación y limpieza de equipos. 
2. 
Verificación de uniones roscadas o soldadas. 
3. 
Verificación y regulación de relés, tensiones e intensidades. 
4. 
Verificación de los equipos de transmisión de alarma. 
5. 
Prueba final con cada fuente de suministro.  
5.1.2.4 
Sistemas manuales de Alarma de Incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Verificación integral de la in
[… contenido truncado para legibilidad]
```

**[F5]** `ZXe` · *1. Verificación integral de la instalación y limpieza de equipos.* · `MIE-MI-530rv001` p.41 · sim 0.68

```
1.
Verificación integral de la instalación y limpieza de equipos.

Paneles de Incendio ZX2e / ZX5e 
 
MORLEY-IAS 
 
Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 41 de 50 
5.1.2 REGLAMENTO DE INSTALACIONES DE PROTECCIÓN CONTRA 
INCENDIOS (R.I.P.C.I) 
 
5.1.2.1 
Sistemas automáticos de Detección de Incendios: Atención trimestral 
La empresa Mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
2. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
3. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
5.1.2.2 
Sistemas manuales de Alarma de Incendio: Atención trimestral 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Comprobación del funcionamiento de los sistemas con cada fuente de suministro. 
Prueba de indicadores y sustitución de pilotos y fusibles defectuosos. 
Mantenimiento de los acumuladores o baterías. Limpieza de bornes, reposición de líquidos, etc… 
 
5.1.2.3 
Sistemas automáticos de Detección de incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
1. 
Verificación integral de la instalación y limpieza de equipos. 
2. 
Verificación de uniones roscadas o soldadas. 
3. 
Verificación y regulación de relés, tensiones e intensidades. 
4. 
Verificación de los equipos de transmisión de alarma. 
5. 
Prueba final con cada fuente de suministro.  
5.1.2.4 
Sistemas manuales de Alarma de Incendios: Atención anual 
La empresa mantenedora, el Usuario o el Titular de la instalación, deberá revisar lo siguiente: 
Verificación integral de la instalación y
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre grupos de presión contra incendios Dorot en mi base de documentación. Los fragmentos disponibles corresponden exclusivamente a paneles de incendio **ZX2e/ZX5e** de Morley-IAS y a la **Serie Dimension Series** de MorleyIAS.

Consulta directamente la documentación técnica del fabricante Dorot para el mantenimiento de ese equipo específico.
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

**Razón del judge:** El bot reconoce correctamente que no dispone de documentación sobre grupos de presión Dorot — ningún fragmento F ni V cubre ese fabricante/producto — y redirige al técnico a la fuente correcta. La mención de los productos disponibles (ZX2e/ZX5e y Dimension Series) es fiel a los fragmentos F recuperados. Conducta admit_no_info ejecutada correctamente.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- Dorot (fabricante de válvulas/grupos de presión hidráulicos) y grupos de presión PCI están fuera del dominio del corpus actual (manuales electrónicos PCI: detección, alarma, evacuación). Verificado: 0 hits. El bot debe admitir y derivar.

**Calidad de los chunks:**

- F1-F5 son chunks de mantenimiento R.I.P.C.I. de ZX2e/ZX5e (Morley) y Serie Dimension — relacionados tangencialmente con "mantenimiento PCI" pero NO con grupos de presión hidráulicos. Retrieval razonable por similitud léxica con "mantenimiento" e "incendios".
- **Patrón de duplicación severa**: F1, F2, F4, F5 son todos del mismo MIE-MI-530 p.41 con headers ligeramente distintos. 4 de 5 slots ocupados por la misma página. Desperdicio masivo de retrieval.

**Comparación con bot:**

- Admitió "no tengo info" correctamente.
- No inventó procedimiento de mantenimiento Dorot.
- Derivó a Dorot.
- **Keyword fail (`grupo presión|grupo de presión` missing)** porque el bot dice "grupos de presión contra incendios" — la regex es frágil. El bot está bien.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo (fuera de dominio). Detectados dos problemas independientes del caso: (1) duplicación masiva de chunks F1=F2=F4=F5, (2) keyword YAML frágil.
- **Origen del problema:** Corpus gap legítimo (grupos de presión hidráulicos fuera de dominio actual); fallo de retrieval por duplicación (4 chunks idénticos ocupando slots útiles).

---

## nd008 — judge dice **PASS ✓** · (8/8)

**Pregunta del técnico:** ¿Cómo doy de alta un lector en el control de acceso CDVI ATRIUM?

**Conducta esperada:** `admit_no_info` · **observada:** `admit_no_info`

**Keyword score:** 5/5 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: Fuera de dominio — control de acceso es futuro._

### Fragmentos que el bot usó (top 5)

**[F1]** `MINILÁSER25` · *7.3 Conexión de un MINILÁSER25 a un Panel de Control direccionable* · `MIDT732` p.32 · sim 0.60

```
7.3 Conexión de un MINILÁSER25 a un Panel de Control direccionable

7.3 Conexión de un MINILÁSER25 a un Panel de Control direccionable

MI-DT-732_C
32
Manual de instalación del detector Miniláser 25
7.3 Conexión de un MINILÁSER25 a un Panel de Control direccionable
Es posible usar una tarjeta interfaz de protocolo direccionable (APIC) para descifrar la
información del detector y transmitirla al panel de control.
La tarjeta APIC se colocará sobre los cuatro pernos de montaje en la tarjeta de lazo del
MINILÁSER25, utilizando los tornillos suministrados según muestra la siguiente imagen:
Interruptor de
Direccionamiento
APIC x 2
Conexión
Interfaz
APIC
Pernos de
Montaje x 4
Las conexiones al Panel de Control se realizan usando los conectores de BUS L1
(bajo -) y H1 (alto +) (entrada y salida bus 1) y BUS L2 (-) y H2 (+) (entrada y salida bus
2) según se indica en la sección 6.2.2. Los únicos ajustes necesarios se realizan en los
interruptores de direccionamiento APIC. La dirección inicial de lazo se introduce en el
interruptor SW1, mientras que la dirección final de lazo se introduce en el interruptor
SW2. En el caso de disponer de un sólo detector MINILÁSER25, la dirección inicial y
final es la misma.
La dirección del detector en la red SenseNET y la dirección del protocolo direccionable
del Panel de Control contra incendios son iguales, es decir que no se realiza ninguna
traducción de dirección. Es posible que algunos protocolos no toleren todos los niveles
disponibles de alarma por lo que el informe de averías normalmente indicará una
avería general sin ninguna información detallada de la avería. Consulte la documentación
específica del protocolo APIC si desea  más información.
Nota:
```

**[F2]** `unknown` · *4- Guía de Configuración* · `TCD-100 Tarjeta comunicadora a CRA ES GB` p.8 · sim 0.58

```
4- Guía de Configuración

8
ES
4- Guía de Configuración
La configuración de la tarjeta TCD-100 puede realizarse a través de distintas vías en 
función del tipo de panel (Analógico o Convencional) en el que se pretenda llevar a 
cabo la instalación.
Si está instalando la tarjeta en un Panel Convencional o en un Panel Analogico sin 
usar la conexión a la tarjeta de red, podrá configurar la tarjeta usando:
- Si su tarjeta dispone de módulo GSM, mediante un teléfono móvil, enviando SMS 
de configuración a la tarjeta SIM instalada en el módulo TCD-100.
- Si su tarjeta dispone de módulo Ethernet o ha adquirido el cable de configuración 
de RS-485, puede utilizar el software  “JR elight”.
Si está instalando la tarjeta en un Panel Analógico, conectándola a través del bus 
rs-485 a la tarjeta de red del panel, podrá configurar la tarjeta mediante los métodos 
mencionados anteriormente y además: 
- Usando el menu de configuración de la central
Si esta usando la tarjeta en un panel Convencional Detnov y dispone de la tarjeta de 
expansión RS-485 y el cable de configuración de centrales convencionales Detnov, 
puede configurarla usando el software del sistema convencional.
4.1 Configuración usando un teléfono móvil.
Para configurar la tarjeta usando un teléfono móvil será necesario tener ya instalada 
la tarjeta SIM en el módulo TCD-100 como se explica en el punto 3, sección 3.1 de 
éste manual, puesto que los mensajes de configuración serán enviados al número 
asociado a dicha tarjeta SIM.
Después de enviar cada mensaje de configuración, usted recibirá un mensaje de 
respuesta con el texto “1 item programmed” como indicación de que la programación 
se ha realizado correctamente.  Es importante que al configurar los parámetros 
relacionados con números telefónicos, introduzca siemp
[… contenido truncado para legibilidad]
```

**[F3]** `LaserStar-HSSD-2` · *resultar dañado.* · `MIDT731` p.52 · sim 0.60

```
resultar dañado. (continuación)

[TABLA EXTRAÍDA]
|  |  |  |  | Manual de insta | lación | del | det | ector HSSD-2
----------------------------------------
14. | Clasificación SE | LV ( | EN6095 | 0) | Clase III |  |  |  | 
Especificaciones | Voltaje de alimen | taci | ón |  | 21,6V - 26,4V DC |  |  |  | 
LaserStar-HSSD-2 |  |  |  |  | Tipo FA: conforme La seguridad eléc | EN 5 trica c | 4-4 umpl | e c | on BS EN
 |  |  |  |  | 610190-1 |  |  |  | 
NOTA: Este equipo |  |  |  |  |  |  |  |  | 
sólo debe funcionar | Tamaño (mm) |  |  |  | 427 (ancho) x 372 | (alto) | x 95 | (fo | ndo)
según estas |  |  |  |  |  |  |  |  | 
 |  |  |  |  | 5,2 kg (Detector); | 5,3 kg | (Det | ecto | r con Módulo
especificaciones, de | Peso |  |  |  | Control); 6,2 k | g (M | ódu | lo | de Control
lo contrario podría |  |  |  |  | independiente); 1 | 0,1 kg | (Mó | dul | o de Control
resultar dañado. |  |  |  |  | independiente + B | atería | s) |  | 
 | Temperatura de | func | ionamie | nto | -10 a +38ºC |  |  |  | 
 | Humedad de fun | cion | amiento |  | 0 - 90% no conde | nsada |  |  | 
 |  |  |  |  | BS EN 61010-1 N | ivel de | con | tam | inación 1
 |  |  |  |  | BS EN 61010-1 In | stalac | ión C | at | egoría II
 | Sensibilidad (% | oscu | recimie | nto /metro) | Mín = 25% Máx | = 0,03 | % |  | 
 | Resolución máxi | ma | de la se | nsibilidad | 0,0015 % Oscure | cimien | to / | met | ro
 | Principio de Dete | cci | ón |  | Detección de mas | a por d | ispe | rsió | n de luz láser
 | Sensibilidad ante | pa | rtículas |  | de 0,0003μm hast | a 10 |  |  | 
 | Consumos |  |  |  | Detector: 300mA | (veloci | dad | de | ventilador 1);
 |  |  |  |  | 470mA (velocid | ad ve | ntila | do | r 8); 750mA
 |  |  |  |  | (velocidad de vent | ilador | 16) |  | 
 |  |  |  |  | Detector módulo d | e c
[… contenido truncado para legibilidad]
```

**[F4]** `unknown` · *6. Alimentación* · `TCD-100 Tarjeta comunicadora a CRA ES GB` p.8 · sim 0.57

```
6. Alimentación

6. Alimentación

8
ES
4- Guía de Configuración
La configuración de la tarjeta TCD-100 puede realizarse a través de distintas vías en 
función del tipo de panel (Analógico o Convencional) en el que se pretenda llevar a 
cabo la instalación.
Si está instalando la tarjeta en un Panel Convencional o en un Panel Analogico sin 
usar la conexión a la tarjeta de red, podrá configurar la tarjeta usando:
- Si su tarjeta dispone de módulo GSM, mediante un teléfono móvil, enviando SMS 
de configuración a la tarjeta SIM instalada en el módulo TCD-100.
- Si su tarjeta dispone de módulo Ethernet o ha adquirido el cable de configuración 
de RS-485, puede utilizar el software  “JR elight”.
Si está instalando la tarjeta en un Panel Analógico, conectándola a través del bus 
rs-485 a la tarjeta de red del panel, podrá configurar la tarjeta mediante los métodos 
mencionados anteriormente y además: 
- Usando el menu de configuración de la central
Si esta usando la tarjeta en un panel Convencional Detnov y dispone de la tarjeta de 
expansión RS-485 y el cable de configuración de centrales convencionales Detnov, 
puede configurarla usando el software del sistema convencional.
4.1 Configuración usando un teléfono móvil.
Para configurar la tarjeta usando un teléfono móvil será necesario tener ya instalada 
la tarjeta SIM en el módulo TCD-100 como se explica en el punto 3, sección 3.1 de 
éste manual, puesto que los mensajes de configuración serán enviados al número 
asociado a dicha tarjeta SIM.
Después de enviar cada mensaje de configuración, usted recibirá un mensaje de 
respuesta con el texto “1 item programmed” como indicación de que la programación 
se ha realizado correctamente.  Es importante que al configurar los parámetros 
relacionados con números telefónicos, introduz
[… contenido truncado para legibilidad]
```

**[F5]** `MINILÁSER25` · *SCRN: SCREEN: Pantalla del cableado* · `MIDT732` p.31 · sim 0.60

```
SCRN: SCREEN: Pantalla del cableado (continuación)

[TABLA EXTRAÍDA]
|  | M | anual de instalac | ió | n del | detector | Min | iláser 25
----------------------------------------
7.2 Conexión del | MINILÁSER25 | a una red de | detectores Se | n | seNE | T / RS4 | 85 | 
SCRN: SCREEN: P | antalla del cablea | do |  |  |  |  |  | 
Se pueden conectar | hasta 127 detecto | res en un sólo | bus SenseNET, | so | porta | ndo una l | ong | itud
total de cableado de | 1,2 km como má | ximo entre dete | ctores adyacent | es | . |  |  | 
En el ejemplo anterio | r, dos detectores | MINILÁSER25 | se unen en un b | us | de 1 | 27 detect | ore | s con un
Módulo de Control y | varios detectore | s LaserStar-HS | SD 2. Obsérves | e | que, | mientras | los | equipos
LaserStar-HSSD 2 ti | enen dos buses d | e entrada y sali | da (1A / 1B y 2A | / | 2B), e | l MINILÁ | SER | 25 sólo
posee un único bus | de este tipo (A / B) | y por consigui | ente, cada termin | a | l del | bus tiene | un | cable de
entrada y uno de sal | ida, y no un sólo | cable como en | cada terminal de | l | Laser | Star-HSS | D 2 | .
Por este motivo sería | más fácil empalm | ar los cables d | e entrada y salida | p | ara c | ada cone | xión | de bus
y pantalla y unir un ú | nico cable con cad | a par de cable, | para que resulte | m | ás fá | cil introdu | cirlo | s en los
terminales. Una vez | hecho esto, se re | comienda aisla | r los empalmes | co | n los | cables p | elad | os para
evitar un posible cort | ocircuito del bus | de datos, ya qu | e provocaría una |  | pérdid | a de dat | os e | n el bus
MI-DT-732_C
32
Manual de instalación del detector Miniláser 25
7.3 Conexión de un MINILÁSER25 a un Panel de Control direccionable
Es posible usar una tarjeta interfaz de protocolo direccionable (APIC) para descifrar
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
No tengo información sobre el sistema de control de acceso **CDVI ATRIUM** en mi base de documentación. Los fragmentos recuperados corresponden a productos de detección de incendios por aspiración (MINILÁSER25, LaserStar-HSSD-2) y una tarjeta comunicadora (TCD-100), que no tienen relación con el equipo que consultas.

Consulta directamente la documentación técnica del fabricante CDVI o contacta con su soporte técnico para el procedimiento de alta de lectores en el sistema ATRIUM.
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

**Razón del judge:** El bot no hace afirmaciones técnicas inventadas: reconoce correctamente que ningún fragmento (F ni V) cubre el sistema CDVI ATRIUM, identifica con precisión los productos que sí aparecen en los fragmentos recuperados, y redirige al técnico al fabricante. Esto es un admit_no_info honesto y útil, alineado con la conducta esperada.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

- CDVI y el sistema ATRIUM (control de acceso) son fuera de dominio PCI. Verificado: 0 hits en manuales reales. Control de acceso es categoría "futura" según las notas YAML. El bot debe admitir y derivar.

**Calidad de los chunks:**

- F1, F3, F5 son detección por aspiración (MINILÁSER25, LaserStar-HSSD-2); F2 y F4 son la misma página de TCD-100 (tarjeta comunicadora a CRA) — **duplicación**.
- F3 contiene `[TABLA EXTRAÍDA]` con formato pésimo (cuadrícula con celdas dislocadas) — patrón de extracción de tabla mal aplicada que ya hemos visto en otros casos.
- Retrieval ruidoso por similitud léxica con "configuración"/"conexión"/"alta", pero ningún chunk de control de acceso. Sin retrieval miss.

**Comparación con bot:**

- Admitió "no tengo info" correctamente.
- Identificó explícitamente los productos cubiertos (MINILÁSER25, LaserStar-HSSD-2, TCD-100) — buena delimitación.
- No alucinó procedimiento de alta de lectores.
- Derivó a CDVI.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso `not_in_db` legítimo (control de acceso fuera de dominio). Detectados patrones: (1) duplicación F2=F4, (2) `[TABLA EXTRAÍDA]` mal aplicado en F3.
- **Origen del problema:** Corpus gap legítimo (control de acceso fuera de dominio actual).

---

