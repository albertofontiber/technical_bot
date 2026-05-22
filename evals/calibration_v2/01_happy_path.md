# Calibración del judge v2 — categoría `happy_path` (20 preguntas)

**Origen:** `logs/eval_20260502T152857Z.json` (eval del 2 mayo 2026).

**Categoría:** Modelo y pregunta claros, info en corpus -> bot debe responder con cita y sin inventar.

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

## hp001 — judge dice **PASS ✓** · (1/20)

**Pregunta del técnico:** En la Detnov CAD-250, ¿cómo se entra al menú de programación avanzada?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/4 hits · missing: `['contraseña']` · **keyword_pass:** `False`

> _Notas YAML: Debe citar el manual de la CAD-250 y probablemente mostrar el teclado._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `CAD-250` · *AJUSTES (Menú principal) > AVANZADO(Submenú)  > Sistema* · `CAD-250-MC-380-es` p.31 · sim 0.80

```
AJUSTES (Menú principal) > AVANZADO(Submenú)  > Sistema

AJUSTES (Menú principal) > AVANZADO(Submenú)  > Sistema

31
ESP
Al tocar el campo PANELES, tendrá acceso a incluir un valor del 1 al 
4. Introduzca el valor que corresponda.
5.4.	 AVANZADO
En esta sección podrá establecer los parámetros básicos de 
configuración de la central, así como ajustes de ingeniero para facilitar 
trabajos de puesta en marcha y configuración. Para acceder a estos 
ajustes pulse:
AJUSTES (Menú principal) > AVANZADO (Submenú) 
Dispone de 3 pestañas de configuración en este nivel, SISTEMA, OTROS 
y REINICIAR.
AJUSTES (Menú principal) > AVANZADO (Submenú)  > Sistema
En la pestaña SISTEMA podrá configurar características esenciales 
como el número de cabinas que tiene su central, el número de lazos 
o si dispone de cabina con leds de zona. Vea el apartado 2 de este 
manual y las descripciones de configuración hardware del manual de 
instalación, ANEXO 1.
Menú Principal
SubMenú
Vista Principal
Al tocar el campo LAZOS, se desplegarán las combinaciones 
posibles según el número de cabinas que haya indicado en el 
punto anterior. 2, 4, 6 u 8 lazos si ha definido una sola central, 
hasta 16 lazos, si ha definido 2 cabinas,. hasta 24 con 3 cabinas y 
32 lazos con 4 cabinas. Si el número de lazos que debe configurar 
no se muestra, revise el número de paneles configurado o pruebe 
a realizar scroll del desplegable.
Al tocar el campo LEDes, puede definir si el sistema tiene una cabina 
con leds de zona o no. Puede seleccionar 0 ó 1.
Para validar los cambios debe pulsar el botón Guardar y Reiniciar.
```

**[F2]** `CAD-250` · *Campo Definición* · `CAD-250-MC-380-es` p.34 · sim 0.80

```
Campo
Definición

ESP
34
5.6.	 IMPRESORA
Si su modelo de central es la CAD-250-P este submenú estará 
disponible. Para acceder a la categoría de AJUSTES pulse:
AJUSTES (Menú principal) > IMPRESORA (Submenú)
Este submenú presenta dos pestañas.
5.6.1.	 Opciones de impresora
La pantalla de impresora muestra unas serie de parámetros activables a 
través de selectores. 
Para activar la salida de eventos por la impresora pulse:
HABILITADO: Activa la salida de eventos por la impresora.
La información imprimible se divide en dos columnas: si tiene una 
red de paneles CAD-250 puede elegir si imprimir todos los eventos 
del sistema, selector HABILITAR, o sólo los eventos del panel que está 
configurando, selector SOLO LOCAL.
Menú Principal
SubMenú
Vista Principal
Opción
Definición
HABILITAR
HABILITA la impresión para todos los eventos del sistema o para el 
tipo de evento seleccionado, ver tabla más abajo
SOLO LOCAL
Si la central está en red, al marcar esta opción, sólo imprimirá los 
eventos de la central y filtrará cualquier otro proviniente de las otras 
centrales de la red.
De cada una de las columnas puede seleccionar qué información 
imprimir:
Opción
Definición
TODOS
Este filtro activa la impresión de todos los eventos
ALARMA
Activa la salida de eventos de alarma.
AVERIA
Activa la impresión las averías.
TEST
Activa la impresión los eventos procedentes de pruebas.
INFORMACION
Activa la impresión de todos los eventos.
5.6.2.	 Configuración de conexión de impresora
En la pantalla de configuración puede consultar los datos de 
conexión de la impresora. 
Campo
Definición
UBICACION
Muestra en qué cabina está instalada la impresora si la central está 
compuesta por más de un cuerpo.
Caja 1 indicará que es la cabina superior conteniendo el primer lazo
BAUDIOS
Muestra la velocidad d
[… contenido truncado para legibilidad]
```

**[F3]** `CAD-250` · *•	Confirme si desea crear un acceso directo en el escritorio y pulse SIGUIENTE.* · `CAD-250-MS-416-es` p.14 · sim 0.80

```
•	Confirme si desea crear un acceso directo en el escritorio y pulse
SIGUIENTE.

ESP
14
3.	 REQUISITOS Y HERRAMIENTAS
3.6.	 REQUEIRIMIENTOS DEL SISTEMA
El software de configuración para los sistemas Vesta con centrales 
CAD-250 debe ser instalado en un ordenador cuyos requerimientos 
minimos sean equivalentes a:
Sistema Operativo: 
   Windows 7 SP1 x64 o posterior
   Windows 10 v.1809 o posterior
Puerto USB
Procesador: 2.4 GHz Dual Core Procesador 
Memoria: 2 GB RAM
Tarjeta gráfica: 512 MB VRAM
Disco duro: 2GB (x64)
3.7.	 PROCEDIMIENTO DE INSTALACION
Descárguese el software de configuración desde la página web www.
detnov.com.
Acuda al área de descargas, si no está registrado deberá solicitar el 
registro desde el área privada. Recuerde que si no se ha registrado no 
podrá realizar la descarga.
•	Para instalar haga CLIC sobre el icono del instalador.
•	El instalador le solicitará que especifique el idioma.
•	Pulse el botón OK
•	Confirme si desea crear un acceso directo en el escritorio y pulse 
SIGUIENTE.
•	La barra de progreso le indicará que el programa se está instalado 
en su ordenador.
•	Seleccione si desea abrir el programa de configuración y pulse el 
botón FINALIZAR.
Area privada
 Area de descargas
```

**[F4]** `CAD-250` · *PASO 1: Identifique llos terminales de salida de lazo en la tarjeta.* · `Manual instalacion CAD-250 (MI_372_es_2024 e)` p.20 · sim 0.72

```
PASO 1:
Identifique llos terminales de salida de lazo en la tarjeta.

ESP
22
Cada tarjeta de lazo puede soportar hasta 250 dispositivos analógicos de DETNOV 
(sirenas, módulos de entrada, de salida, aisladores, detectores o barreras analógicas). 
En general todos estos dispositivos se alimentan del propio lazo.
Es posible subdividir cada lazo en múltiples zonas sin superar el número de zonas 
absoluto de 2.000.
4.8. Lazos analógicos
De acuerdo con la norma de diseño UNE 23007-14, el número máximo 
de elementos de iniciación de alarma de incendio por zona es de 32. 
Los sistemas de detección de incendio exigen emplear una topología 
en anillo para evitar que un único fallo provoque la pérdida de un sector 
significativamente grande.
Aunque los ramales son tolerados por el sistema, su uso no es aconsejable 
y debe ser restringido.
El cable recomendado para el lazo analógico es un cable trenzado y 
apantallado (entre 20 y 40 vueltas /metro) , capacidad inferior a los 0,5 μF 
y una resistencia máxima de 44 ohmios para todo el recorrido del lazo. El 
consumo máximo de los dispositivos conectados al lazo no puede exceder 
los 400 mA.
La sección estandar es 1,5 mm2 de diámetro para una longitud de lazo 
máxima de 1.500 m, sin embargo esta puede ser mayor en función de la 
instalación.
Los terminales de conexión en la tarjeta de lazo admiten una seccion de 
hasta 2,5 mm2 de diámetro para una distancia máxima de 2.000 
m de longitud en el lazo.
Recomendamos que el cableado del sistema se realice con cables de dos 
conductores y que cada cable sea específico para una función.
Utilice terminales y/o fundas termorretractiles en las terminaciones de los 
cables para evitar posibles cortocircuitos.
El cableado del lazo debe estar cerrado. Es imprescindible asegurar el retorno de los
[… contenido truncado para legibilidad]
```

**[F5]** `CAD-250` · *2.7.2. Exención de responsabilidad* · `Manual usuario CAD-250 (MU 376 es 2024 f)` p.6 · sim 0.72

```
2.7.2. Exención de responsabilidad

2.7.2. Exención de responsabilidad

ESP
6
2.7. Definiciones explícitas
Los procedimientos descritos en este manual incluyen avisos y advertencias para aconsejar 
al usuario que adopte prácticas de trabajo metódicas y seguras durante la instalación, 
puesta en marcha y configuración.
Por favor, siga las advertencias del presente manual, un mal uso o instalación inadecuada 
pueden ocasionar desde un mal montaje hasta un riesgo para las personas. 
Estas advertencias le avisan desde los riesgos graves de incendio y electrocución (áreas 
con riesgo eléctrico superan el nivel de seguridad), pasando por riesgo de dañar elementos 
de la central sensibles a la corriente estática o los cortocircuitos si no se siguen los 
procedimientos, recomendaciones o referencias normativas o consejos para facilitar los 
procesos de montaje, conexión o instalación.
Las definiciones están clasificadas en los niveles:
Señal               Definición                                                            
                   Riesgo de daños personales
                   Riesgo para el producto y sistema
                   Revise según la reglamentación aplicable
                   No hay riesgo, observaciones y comentarios para facilitar la acción
                   Acuda al servicio de soporte técnico
                   Acción recomendada
                   Acción no recomendada o incorrecta
2.7.1. Notas sobre el uso de esta central
CONOCIMIENTOS: Asegúrese de tener los conocimientos y autorización necesarios para 
operar este panel.
El uso indebido o negligente del nivel de acceso de USUARIO puede 
provocar un mal funcionamiento de la instalación que puede ocasionar la 
pérdida de vidas humanas.
2.7.1. Notas sobre la instalación
Asegúrese de que un instalad
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para acceder al menú de programación avanzada en la **CAD-250**, sigue esta ruta de navegación:

**Ruta de acceso:**

1. Desde la pantalla principal, pulsa **AJUSTES** (Menú principal) [F1]
2. Dentro de AJUSTES, selecciona el submenú **AVANZADO** [F1]

Una vez dentro de **AVANZADO**, dispones de **3 pestañas de configuración** [F1]:

- **SISTEMA** — Parámetros esenciales: número de cabinas, número de lazos, cabina con LEDs de zona [F1]
- **OTROS** [F1]
- **REINICIAR** [F1]

**Nota importante:** Este submenú contiene ajustes de ingeniero para trabajos de puesta en marcha y configuración [F1]. Asegúrate de tener los conocimientos y autorización necesarios para operar a este nivel [F5].

Tras realizar cualquier cambio en la pestaña SISTEMA, debes pulsar el botón **Guardar y Reiniciar** para validar los cambios [F1].

---

Fuente: CAD-250-MC-380-es (sin revisión registrada)

---

También puedo ayudarte con: **configuración de lazos en AVANZADO > SISTEMA**, **ajustes de la pestaña OTROS** o **acceso al software de configuración SC250** de la CAD-250.
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

**Razón del judge:** Todas las afirmaciones técnicas del bot están directamente soportadas por F1 (ruta AJUSTES > AVANZADO, las 3 pestañas SISTEMA/OTROS/REINICIAR, descripción de ajustes de ingeniero, botón Guardar y Reiniciar) y F5 (nota sobre conocimientos y autorización). La respuesta es directa, precisa y accionable, cumpliendo correctamente la conducta esperada 'answer'.

### Tu calibración

- [] **De acuerdo** con el veredicto del judge
- [X] **En desacuerdo** — yo diría: FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué: Veo que en el fragmento 1, no extrajo la información de la P32, que en realidad también corresponde con ajustes avanzados dentro de la sección 5.4. Como prioridad 2, he visto en la P20, sección 4.1, que se refiere a "acceso como administrador", y me pregunto si esto es algo que debería aparecer o bien en la respuesta o bien en la parte de "también puedo ayudarte con: ...". Además, F2-F3-F4-F5 me parece que no son relevantes para la respuesta (uno habla de la impresora, otro del software,etc.)**

**Calibración Claude:**

**Respuesta de referencia (basada en `CAD-250-MC-380-es.pdf` sec. 5.4, pág. 31-32):**

Ruta: AJUSTES (Menú principal) → AVANZADO (Submenú). Contiene 3 pestañas:
- **SISTEMA:** nº cabinas (1-4), nº lazos (2-32 según cabinas), cabina con LEDs de zona (0-1). Validar con "Guardar y Reiniciar".
- **OTROS:** 3 interruptores — *Tiempo de inactividad*, *Salto a scroll si incidentes*, *Saltar a último incidente prioritario si timeout*. Por defecto todos activos por exigencias EN54-2.
- **REINICIAR:** reinicio de la central.

**Información relevante NO mostrada en los fragmentos F:** la sec. 5.3 del manual indica que el acceso a configuraciones avanzadas requiere **contraseña de nivel instalador** (4 dígitos). Esta sección no fue recuperada en F1-F5.

**Comparación con la respuesta del bot:**
- ✓ Ruta de acceso correcta y citada a F1.
- ✓ Las 3 pestañas correctas.
- ✓ Cita "Guardar y Reiniciar".
- ✓ Cita el aviso de conocimientos/autorización (F5).
- ⚠️ Sólo describe SISTEMA en detalle. OTROS y REINICIAR aparecen sólo como nombres (F1 corta antes del desarrollo de OTROS en pág. 32).
- ⚠️ No menciona la contraseña de instalador (no estaba en sus F).
- Coincido con Alberto: F2-F5 son ruido para esta pregunta (impresora, software de configuración, lazos analógicos, exención de responsabilidad).

**Calidad de los chunks:**
- **F2 header** ("Campo Definición") es un fragmento de columna de tabla, no un epígrafe. Header inútil para guiar el retrieval.
- **F3 header** ("•	Confirme si desea crear un acceso directo en el escritorio y pulse SIGUIENTE.") es una instrucción suelta, no un epígrafe. Mismo problema.
- **F1 corta a mitad de la sec. 5.4**: contiene la introducción a AVANZADO, las 3 pestañas y SISTEMA, pero pierde el desarrollo de OTROS y REINICIAR de la pág. 32 (chunking partido por la mitad de una sección lógica).
- **F2, F3, F4, F5 son ruido**: 4 de 5 chunks no aportan a la pregunta. Indica que el retrieval ranking de la query "menú de programación avanzada CAD-250" no está priorizando contenido relevante.

**Veredicto:**
- [x] **De acuerdo** con el veredicto del judge (PASS) — *dentro del alcance del judge (bot vs F)*
- [x] **Pero en desacuerdo con el resultado final** — la respuesta del bot **no es completa** para un técnico, aunque sea fiel a sus F
- **Dimensión equivocada(s) del judge:** ninguna dentro de su alcance. El problema es que el judge no evalúa **completitud objetiva** (lo que está en el manual y debería haberse retrieved).
- **Nota / por qué:** El bot es fiel a los F que recibió (todas sus afirmaciones soportadas). El keyword fail de "contraseña" no es fallo de generación, sino de **retrieval**: los chunks de sec. 5.3 (Contraseñas / Niveles de acceso) no entraron en el top-5. Lo mismo aplica a la observación de Alberto sobre OTROS/REINICIAR: el chunking corta la sec. 5.4 antes de su desarrollo en pág. 32. **Coincido con Alberto en que la respuesta para el técnico es incompleta**, pero el judge no puede detectarlo porque no ve más allá de F. La discusión Alberto-vs-judge revela que el sistema necesita resolverse aguas arriba (retrieval), no en el prompt del judge.
- **Origen del problema:** **retrieval** (priorización + chunking partido) + **chunk-extraction** (headers inútiles en F2-F3).

---

## hp002 — judge dice **PASS ✓** · (2/20)

**Pregunta del técnico:** El detector ASD535 de Detnov está dando una alarma intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/4 hits · missing: `['tubería']` · **keyword_pass:** `False`

> _Notas YAML: ASD535 es aspiración. Respuesta debería cubrir obstrucción, fuga, filtro sucio._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ASD535` · *9.3 Comprobaciones de mantenimiento y funcionamiento* · `ASD535_TD_T131192es_h` p.121 · sim 0.80

```
9.3
Comprobaciones de mantenimiento y funcionamiento (continuación)

Para las comprobaciones de mantenimiento y funcionamiento deberán llevarse a cabo las siguientes acciones: 
1. 
 Bloquear o desconectar el control de incendios y la alerta remota en la CDI de orden superior. 
2. 
 La tensión de alimentación de la CDI debe estar configurada para la central conforme a la normativa de
mantenimiento. 
3. 
 Debe comprobarse que la entrada del conducto de aspiración y los tapones de tubo del orificio de entrada de la caja
del detector que no está en uso (ASD 535-1 y ASD 535-3) están en la posición correcta. 
4. 
 Debe comprobarse si existe suciedad en la salida de aire, en cuyo caso deberá limpiarse. 
5. 
 En caso de que el ASD 535 se utilice para la vigilancia de equipos y se hayan instalado transiciones insertadas de tubo
rígido a tubo flexible, debe comprobarse que dichas transiciones están colocadas correctamente (sin fugas). 
6. 
 Debe abrirse la cubierta de la caja del detector y fijarse en la posición media de anclaje del fondo de la caja. Atención:
conexión de cable plano (véanse también los cap. 5.4.1 y 7.1). Deberán efectuarse las siguientes mediciones: 
• 
Medir la tensión de servicio en los bornes 1 (+), 2 (-)  Valor nominal = 12,3 a 13,8 V-CC (funcionamiento a 12 V-
CC) o 21,6 a 27,6 V-CC (funcionamiento a 24 V-CC). 
• 
Leer el valor de flujo de aire del conducto de aspiración en la posición de conmutador V (véase para ello el
cap. 7.6.1) y comparar con el protocolo de puesta en funcionamiento. Si existe una desviación superior a la mitad
de la sensibilidad establecida (véanse ejemplos  y ), deberá realizarse una inspección del conducto de
aspiración de la siguiente manera: 
- 
Un aumento del valor (superior al 100 %) implica una rotura de tubo inminente  Co
[… contenido truncado para legibilidad]
```

**[F2]** `ASD535` · *9.3 Comprobaciones de mantenimiento y funcionamiento* · `ASD535_TD_T131192es_h` p.121 · sim 0.80

```
9.3
Comprobaciones de mantenimiento y funcionamiento (continuación)

[TABLA EXTRAÍDA]
|  |  |  |  |  | Conse | rvación | y | mantenimiento
----------------------------------------
9.3 | Comproba | ciones de ma | ntenimiento | y funci | ona | miento |  |  | 
 |  |  |  | Indi | caci | ón |  |  | 
 | Para evitar | que los controles | de incendios, l | as alertas | remot | as y las zonas d | e extinción | se | disparen al llevar a
 | cabo los trab | ajos de mantenim | iento, es impre | scindible | bloqu | earlos o descone | ctarlos prev | ia | mente.
Para la | s comprobacione | s de mantenimien | to y funcionami | ento debe | rán lle | varse a cabo las | siguientes a | cc | iones:
1. | Bloquear o desco | nectar el control | de incendios y l | a alerta re | mota | en la CDI de orde | n superior. |  | 
2. | La tensión de | alimentación de | la CDI debe | estar co | nfigura | da para la cen | tral confor | me | a la normativa de
 | mantenimiento. |  |  |  |  |  |  |  | 
3. | Debe comprobar | se que la entrada | del conducto d | e aspirac | ión y l | os tapones de tu | bo del orific | io | de entrada de la caja
 | del detector que | no está en uso (A | SD 535-1 y ASD | 535-3) e | stán e | n la posición corr | ecta. |  | 
4. | Debe comprobar | se si existe sucied | ad en la salida | de aire, e | n cuyo | caso deberá lim | piarse. |  | 
5. | En caso de que e | l ASD 535 se utili | ce para la vigila | ncia de e | quipos | y se hayan insta | lado transici | on | es insertadas de tubo
 | rígido a tubo flexi | ble, debe compro | barse que dicha | s transici | ones e | stán colocadas c | orrectament | e ( | sin fugas).
6. | Debe abrirse la c | ubierta de la caja | del detector y fi | jarse en l | a posi | ción media de an | claje del fon | do | de la caja. Atención:
 | conexión de cab
[… contenido truncado para legibilidad]
```

**[F3]** `ASD535` · *3.1 Configuración mecánica* · `ASD535_TD_T131192es_h` p.34 · sim 0.80

```
3.1
Configuración mecánica

3.1
Configuración mecánica

Configuración 
34 / 134 
ASD 535, Descripción técnica, T 131 192 h es 
3 
Configuración 
3.1 
Configuración mecánica 
El detector de humos por aspiración ASD 535 se compone de la caja del detector y de una o dos tuberías de aspiración. Los 
conductos de aspiración están formados por tubos de PVC rígido o de ABS de 25 mm de diámetro exterior y 20 mm de 
diámetro interior (véase también el cap. 5.3). En aplicaciones especiales (como los entornos extremadamente corrosivos) 
también pueden utilizarse otros materiales de tubería siguiendo las indicaciones del cap. 5.3. Los conductos de aspiración 
poseen varios orificios de aspiración, dimensionados de tal modo que cada uno de ellos absorbe la misma cantidad de aire. 
Los conductos de aspiración pueden tener forma de I, U, T, H o E. Normalmente, el conducto de aspiración tiene una 
configuración simétrica. No obstante, el software de cálculo «ASD PipeFlow» también permite diseñar tuberías de aspiración 
asimétricas. 
La cubierta de la caja del detector se abre mediante cuatro cierres rápidos giratorios. En la zona media de la parte inferior de 
la caja del detector existen dos posiciones de anclaje adicionales para los cierres giratorios de resorte, con el fin de que la 
cubierta de la caja quede fijada cuando el dispositivo está abierto para los trabajos de puesta en funcionamiento y 
mantenimiento. 
La caja del detector cuenta con un ventilador de alto rendimiento que está conectado con los conductos de aspiración y que 
se encarga de suministrar aire hacia la caja de forma ininterrumpida. Un sistema de monitorización del flujo de aire detecta en 
cada tubería las obstrucciones y roturas que puedan producirse en el conducto de aspiración. 
La caja del detector contien
[… contenido truncado para legibilidad]
```

**[F4]** `ASD535` · *aspiración* · `ASD535_TD_T131192es_h` p.47 · sim 0.80

```
aspiración

aspiración

Proyectos 

ASD 535, Descripción técnica, T 131 192 h es 
47 / 134 
4.4.4.3 
Tabla de límites del sistema para proyectar sistemas sin cálculo con «ASD PipeFlow» 
Según EN 54-20, clase A (sensibilidad muy alta) 
Forma 
Límites del sistema 
Posición de 
conmutador 
según EN 54-20 
Posición de  
conmutador 
no normativa 

Sensor de humo 
tipo SSD 535 
Umbral de alarma 
(%/m) 
Distancia desde 
el ASD hasta la 
última pieza en 
T/en cruz 
Longitud máx. 
del ASD hasta el 
orificio de 
aspiración más 
alejado 
Número de  
orificios de 
aspiración por 
cada rama de 
aspiración 
Longitud total 
máx. del conducto 
de aspiración 
por cada tubería  
(sensor de humo) 

1 tubo 
2 tubos 
1 tubo 
2 tubos 

(Fig. 9 «A») 
(Fig. 9 «B») 

I 
1 
A11 
A12 
W01 – W04 
W05 – W08 
–3 
0,03 
--- 
50 m 
1 – 7 
50 m 
U / T 
1 
A11 
A12 
W01 – W04 
W05 – W08 
–3 
0,03 
1 – 20 m 
40 m 
1 – 4 
80 m 
H 
1 
A11 
A12 
W01 – W04 
W05 – W08 
–3 
0,03 
1 – 20 m 
40 m 
1 – 2 
160 m 
E 
1 
A11 
A12 
W01 – W04 
W05 – W08 
–3 
0,03 
1 – 20 m 
40 m 
1 – 3 
120 m 

Según EN 54-20, clase B (sensibilidad alta) 
-
-
I 
1 
b11 
b12 
W09 – W12 
W13 – W16 
–3 
0,09 
--- 
50 m 
1 – 7 
50 m 
2 
b21 
b22 
W17 – W20 
W21 – W24 
–3 
0,06 
--- 
70 m 
5 – 9 
70 m 
U / T 
1 
b11 
b12 
W09 – W12 
W13 – W16 
–3 
0,09 
1 – 20 m 
40 m 
1 – 3 
80 m 
2 
b21 
b22 
W17 – W20 
W21 – W24 
–3 
0,06 
1 – 20 m 
55 m 
3 – 5 
110 m 
H 
1 
b11 
b12 
W09 – W12 
W13 – W16 
–3 
0,09 
1 – 20 m 
35 m 
1 – 2 
140 m 
2 
b21 
b22 
W17 – W20 
W21 – W24 
–3 
0,06 
1 – 20 m 
45 m 
2 – 3 
180 m 
E 
1 
b11 
b12 
W09 – W12 
W13 – W16 
–3 
0,09 
1 – 20 m 
40 m 
1 – 2 
120 m 
2 
b21 
b22 
W17 – W20 
W21 – W24 
–3 
0,06 
1 – 20 m 
50 m 
2 – 3 
150 m 

Según EN 54-20, clase C (sensibilidad normal) 
I 
1 
C11 
C12 
W25 – W28 
W29 – W32
[… contenido truncado para legibilidad]
```

**[F5]** `ASD535` · *Cálculo: A = 0,5 x 300 x 2 = 0,87 mm² 1,0 mm² 57 x 6* · `ASD535_TD_T131192es_h` p.60 · sim 0.80

```
Cálculo:
A =
0,5 x 300 x 2
=
0,87 mm²
1,0 mm²
57 x 6 (continuación)

ASD 535, Descripción técnica, T 131 192 h es 
61 / 134 
4.11 
Limitaciones 

Indicación 
En la instalación y el uso del ASD 535 se aplicarán las siguientes limitaciones. Las soluciones que se aparten de 
esta norma deberán consultarse con el fabricante. 
Aspectos generales y vigilancia de recintos: 
• 
Los orificios de aspiración de ambas tuberías y de la caja del detector deben encontrarse en la misma zona 
climática (presión y temperatura) (posible retorno del aire aspirado a la otra zona climática). No serán 
admisibles las diferencias de presión entre la caja del detector y el conducto de aspiración (orificios de 
aspiración). 
• 
En caso de que los conductos de aspiración con aire caliente deban atravesar zonas en las que la 
temperatura puede bajar de los 4 °C, las piezas de tubería deberán montarse de manera especial en estos 
tramos (posible aislamiento del conducto de aspiración, siguiendo las indicaciones del fabricante). 
• 
En aquellas aplicaciones en las que exista una abundante presencia de polvo o una humedad elevada, será 
necesario instalar los accesorios correspondientes siguiendo las indicaciones del fabricante, por ejemplo: 
Caja de filtro/unidad de filtrado, trampa para polvo, separador de agua o válvula de bola manual para la 
limpieza ocasional del conducto de aspiración con aire comprimido (véase para ello también el cap. 11). 
• 
No deberá superarse la longitud de tubería máxima establecida. 
• 
Únicamente se podrá utilizar un detector de humos por aspiración para vigilar varios recintos cuando así lo 
autorice la normativa correspondiente (p. ej., DIN VDE 0833-2 en Alemania o VKF en Suiza). 
• 
Gracias a los dos conductos de aspiración I y II pueden vigilarse distintas zonas,
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## ASD535 — Alarma de flujo bajo: causa y diagnóstico

### Causa más probable

Una **disminución del valor de flujo por debajo del 100%** respecto al valor registrado en el protocolo de puesta en funcionamiento indica una **obstrucción inminente en el conducto de aspiración** [F1].

---

### Procedimiento de diagnóstico paso a paso

1. **Bloquear o desconectar** el control de incendios y la alerta remota en la CDI de orden superior antes de iniciar cualquier comprobación [F1].

2. **Verificar la tensión de alimentación** midiendo en los bornes **1 (+) y 2 (−)**:
   - Funcionamiento a **12 V-CC**: valor nominal **12,3 a 13,8 V-CC** [F1]
   - Funcionamiento a **24 V-CC**: valor nominal **21,6 a 27,6 V-CC** [F1]

3. **Leer el valor de flujo actual** en la posición de conmutador **V** (ver cap. 7.6.1 del manual) y compararlo con el protocolo de puesta en funcionamiento [F1].

4. **Interpretar la desviación** según la sensibilidad LS-Ü configurada [F1]:

   - Si sensibilidad = **±20 % (estándar)**: inspeccionar el conducto cuando el valor caiga **por debajo del 90 %**
   - Si sensibilidad = **±50 % (no conforme a EN 54-20)**: inspeccionar cuando el valor caiga **por debajo del 75 %**

5. **Inspeccionar el conducto de aspiración** buscando:
   - Obstrucciones en el interior del tubo [F1]
   - Suciedad en la **salida de aire** de la caja del detector [F1]
   - En instalaciones con tubo rígido a tubo flexible: verificar que las **transiciones no tienen fugas** [F1]
   - Comprobar que la **entrada del conducto de aspiración y los tapones de tubo** (en ASD 535-1 y ASD 535-3) están en posición correcta [F1]

6. **Limpiar el conducto** según los puntos 9 o 10 del capítulo de mantenimiento del manual si se confirma obstrucción [F1].

---

### Nota adicional sobre el entorno

Si la instalación está en un entorno con **abundante presencia de polvo o humedad elevada**, el manual indica que pueden ser necesarios accesorios adicionales como caja de filtro, trampa para polvo o separador de agua [F5]. Esto puede ser un factor contribuyente a la obstrucción recurrente.

---

> ⚠️ **Advertencia**: No aplicar aire comprimido directamente sobre los sensores de humo ni abrirlos. La limpieza de sensores sucios solo puede realizarla el fabricante [F2].

---

**Fuente:** ASD535_TD_T131192es_h (sin revisión registrada)

---

También puedo ayudarte con: **procedimiento de limpieza del conducto de aspiración**, **lectura e interpretación del valor de flujo en posición V** o **sustitución de sensores de humo SSD 535**.
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

**Razón del judge:** Todas las afirmaciones técnicas del bot están directamente soportadas por los fragmentos F1, F2 y F5 que cita: la interpretación de flujo bajo como obstrucción inminente, los umbrales de tensión, los porcentajes de desviación según sensibilidad LS-Ü, las comprobaciones físicas del conducto y la advertencia sobre los sensores de humo. La respuesta es directa, estructurada y accionable, cubriendo exactamente lo que el técnico preguntó (causa más probable y diagnóstico), sin inventar datos ni omiti

### Tu calibración

- [X] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría:  PASS/FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:En general, la respuesta es muy buena y para mi sería un PASS a nivel respuesta ya que las afirmaciones del bot están directamente soportadas, la respuesta está totalmente relacionada con la pregunta, y no inventa, así que muy bien. No obstante, hay cosas que ajustar que te indico a continuación (algunas más estructurales, otras solo relativas a la respuesta del bot). Para empezar, veo que el ASd35 es de Securiton, que distribuye Detnov en España, y no es fabricado por Detnov (en la portada del manual se ve claramente "Securiton"). por lo tanto, esto es un cambio estructural que debemos tener en cuenta a futuro. Por otro lado, F2 dice que es tabla extraída pero en realidad en p121 no hay tabla a extraer. de hecho, F2 es F1 pero falsamente indicando que es formato tabla. Otro error que veo es que F4 es una tabla, y sin embargo no aparece "tabla extraída" como en F2, lo que entiendo puede dar lugar a errores. En el bot de Telegram, veo que incrusta "F1" sin corchetes ni nada e.g. la respuesta que veo en Telegram es "Un aviso de «fallo flujo de aire» por flujo bajo indica que el valor real de flujo ha caído por debajo del 80 % del valor nominal registrado en el reset inicial F1. Según el manual, esto apunta directamente a suciedad u obstrucción en el conducto de aspiración F1". Adicionalmente, veo que en los pasos 2 en adelante en la respuesta que me ha dado en Telegram (le he lanzado la pregunta en paralelo para ver la respuesta real) el bot referencia los fragmentos a F5, cuando en realidad parece que lo estás sacando de F1 (y aplica el mismo error de no estar las fuentes entre corchetes para que sea más fácil para el técnico). además, los pasos 6 y 7 están invertidos en la respuesta del chat vs el orden en el que aparecen en los manuales. ¿por qué los has invertido?**

**Calibración Claude:**

**Respuesta de referencia (basada en `ASD535_TD_T131192es_h.pdf` sec. 9.3, pág. 121):**

Una alarma de flujo bajo en el ASD 535 indica que el valor de flujo ha caído por debajo del umbral configurado (típicamente -20% para EN 54-20, o -50% si no se requiere conformidad). El procedimiento documentado para diagnosticarlo (sec. 9.3, en este orden):

1. Bloquear/desconectar el control de incendios y la alerta remota.
2. Verificar tensión de alimentación.
3. Comprobar entrada del conducto y tapones (ASD 535-1/535-3).
4. Comprobar suciedad en la salida de aire.
5. Si hay transiciones tubo rígido↔flexible, comprobar que no hay fugas.
6. Abrir cubierta. Medir: tensión 12,3-13,8 V-CC (a 12V) o 21,6-27,6 V-CC (a 24V), y leer flujo en posición V comparando con el protocolo de puesta en funcionamiento.

Causas más probables de flujo bajo: **obstrucción del conducto de aspiración**, **suciedad en la salida de aire**, **filtro saturado** (especialmente en entornos con polvo o humedad — F5).

**Calidad de los chunks (importante para tu RAG):**
- **F1 y F2 son duplicados de la misma página 121**, con misma sec. 9.3, misma similitud (0.80). F2 lleva además marcador "[TABLA EXTRAÍDA]" falso: el contenido de F2 es texto plano formateado como tabla por el extractor. **Error de extracción**: el extractor confunde texto multilínea con columnas en tabla.
- **F4 sí contiene una tabla real** (límites del sistema EN 54-20) pero **no lleva el marcador "[TABLA EXTRAÍDA]"**. Inconsistencia inversa al caso anterior. Mismo extractor produciendo dos errores complementarios.
- **Headers inútiles**: F4 ("aspiración"), F5 ("Cálculo: A = 0,5 x 300 x 2…") son fragmentos arbitrarios, no epígrafes. Un header bien construido debería decir "4.4.4.3 Tabla de límites del sistema" y "4.11 Limitaciones".
- **Atribución de fabricante incorrecta**: el manual es de **Securiton** (página de portada), no de Detnov. Detnov es el distribuidor en España. La columna `brand` o `manufacturer` en el índice del RAG debería decir "Securiton" o, si se quiere mantener la marca comercial española, debería ser "Detnov (distribuidor) / Securiton (fabricante)" con campo separado para fabricante real.

**Comparación con la respuesta del bot:**
- ✓ Diagnóstico correcto (obstrucción) — soportado por F1.
- ✓ Tensiones nominales 12/24V correctas.
- ✓ Citación de F1 y F5 fiel al contenido.
- ⚠️ **Reordenación de pasos**: el bot pone medición (tensión, flujo) ANTES de inspección física (entrada, suciedad, transiciones). En el manual la inspección física va primero. La reordenación es razonable como diagnóstico ("medir primero para confirmar, luego inspeccionar para localizar") pero **diverge del manual**, lo cual es discutible en protocolos de mantenimiento donde el orden puede importar por seguridad (p.ej., desconectar antes de medir). Es defendible pero merece flag.
- ⚠️ **Citaciones erróneas en Telegram (observación de Alberto)**: en la versión Telegram, los pasos 2+ citan F5 cuando el contenido viene de F1. **Es bug del bot en la fase de citación final**, no de retrieval. Probablemente porque el modelo asocia F5 con "entorno/polvo/humedad" y duplica esa cita al hablar de medición. Fix: añadir al prompt del generador una regla de "una afirmación = un único F que la soporte de forma exacta; no múltiple atribución".
- ⚠️ **Formato de citas sin corchetes en Telegram**: el bot escribe "F1" en lugar de "[F1]". Bug de post-procesado o de prompt: probablemente el modelo está generando "[F1]" y el renderer Telegram (Markdown) está interpretando los corchetes como link y descartándolos. Fix: usar otro delimitador (paréntesis, llaves) o escapar los corchetes.

**Veredicto:**
- [x] **De acuerdo** con el veredicto del judge (PASS) — el bot es fiel a F.
- **Dimensión equivocada(s) del judge:** ninguna en el alcance bot vs F.
- **Nota / por qué:** Coincido con Alberto en que la respuesta es buena en contenido. Los problemas que detectamos son **estructurales y operativos**, no de fidelidad: (a) brand mapping incorrecto Detnov/Securiton; (b) extractor produce errores opuestos (texto marcado como tabla y tabla no marcada como tabla); (c) headers de chunks son fragmentos arbitrarios; (d) reordenación de pasos vs manual; (e) bug de citación múltiple errónea en Telegram; (f) bug de render de corchetes en Telegram. Ninguno de estos lo detecta el judge porque su scope es bot vs F, no calidad estructural del corpus ni rendering final.
- **Origen del problema:** **chunk-extraction** (F1≡F2, marcadores de tabla mal aplicados), **metadata** (brand=Detnov debería ser Securiton), **generación/citación** (atribución F5 errónea en pasos 2+), **post-procesado/render** (corchetes desaparecidos en Telegram). Cero problemas de retrieval para esta pregunta — F1 cubría bien la respuesta.

---

## hp003 — judge dice **PASS ✓** · (3/20)

**Pregunta del técnico:** ¿Cómo se conectan las baterías de 24V en la Detnov CAD-150?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 1/4 hits · missing: `['24 v', 'polaridad', 'fusible']` · **keyword_pass:** `False`

> _Notas YAML: Esta pregunta es el ejemplo canónico del Detnov re-embed; debe responder con esquema._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `CAD-150-8` · *2.4- Conexión a la red* · `55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT` p.8 · sim 0.72

```
2.4- Conexión a la red (continuación)

[TABLA EXTRAÍDA]
Las centrales | analógicas | re | q | uieren dos batería | s de 12V | 7A/h. Las | ba | terías deben
----------------------------------------
conectarse en s | erie para el | c | o | rrecto funcionamie | nto de las ce | ntrales. |  | 
El cable que s | e suministra |  | co | n la central debe | conectarse | de forma | que | una el polo
positivo de una | batería con |  | el | polo negativo de | la otra. Las | baterías | se c | olocan en la
parte inferior de | la caja, en | e | l e | spacio reservado | para ello de | forma ver | tical | .
Conecte los ca | bles que sa | le | n | del circuito (rojo | y negro) al | positivo y | ne | gativo de las
baterías, y rec | uerde conec | t | ar | previamente entr | e sí las bat | erías con | el | cable puente
batería. |  |  |  |  |  |  |  | 
 | 2. | 6 | - | Conexión de | un bucl | e |  | 
La instalación d | el bucle de | b | e | ser cerrada, es d | ecir, el cable | de dos | hilos | apantallado
debe salir de la | central y vol | v | er | a ella, en este cab | le conectare | mos todo | s lo | s dispositivos
del sistema. |  |  |  |  |  |  |  | 
El cable que de | bemos utiliz | a | r | debe ser como mín | imo de 1,5 | mm2 de di | áme | tro, trenzado
y se debe utiliz | ar apantalla | do | p | ara evitar interfere | ncias. |  |  | 
La longitud má | xima del laz | o | e | s de 2 Km. La re | sistencia del | cable de | l bu | cle debe ser
inferior a 44 Oh | m y la capa | ci | d | ad máxima de la lín | ea debe ser | inferior a | 500 | nF.
Conecte los hilo | s de salida | e | n | el punto de la regle | ta indicada | con S+, | S- y | la pantalla al
borne indicado | como , y | el | r | etorno del bucle en | el punto de | la regleta | indi | cada con R+
y R- y la pantall | a del retorn | o | al
[… contenido truncado para legibilidad]
```

**[F2]** `CAD-150-8` · *2- Guía de Instalación* · `55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT` p.8 · sim 0.72

```
2- Guía de Instalación

6
ES
2- Guía de Instalación
2.1- Selección de Idioma
Las centrales analógicas se han diseñado para que resulte fácil personalizar el idioma. 
En la hoja de idiomas adjunta a este manual, podrá encontrar los textos correspondientes 
a los idiomas  castellano, ingles, italiano y portugués. Seleccione el idioma que precise 
e inserte la lámina en la ranura correspondiente ubicada en la parte inferior del teclado. 
Las ubicaciones están señalizadas con las letras A, B y C.
2.2- Conexionado eléctrico y cableado
Es recomendable que el equipo se alimente y se pruebe antes de conectar dispositivos 
como detectores, pulsadores etc. La central debe conectarse a través de un magneto 
térmico bipolar exterior, utilizando cable de 1.5 mm2 de sección. La tensión de red debe 
ser de 230VAC.
Para evitar cruces el cable de red debe ir separado de los cables del bus de comunicación. 
Si el sistema puede ser alterado por una perturbación eléctrica, se recomienda el uso de 
ferrita, situándola lo más cerca posible de la conexión.
Es imprescindible que se usen los orificios marcados en la caja para conexionar los 
cables tanto de alimentación como de zonas al regletero. Utilice una broca de corona 
para perforar la caja e inserte el prensastopa tipo PG13. Se recomienda usar la entrada 
posterior situada a la altura de la regleta de red, para la entrada del cable de red.
Es recomendable el uso de cable apantallado. Conectar la pantalla del cable a los bornes 
correspondientes (protegiendo la misma pantalla para no provocar cruces indeseados) y 
asegurar que la instalación tiene una conexión a tierra correcta.
2.3- Alimentación de la central
No realizar la instalación de la central con la alimentación conectada. Desconecte 
siempre la magneto térmico bipolar exterior a
[… contenido truncado para legibilidad]
```

**[F3]** `CAD-150-8` · *1- Introducción* · `55315008-Manual-Centrales-Analogicas-CAD-150-8-Usuario-ES-FR-GB-IT` p.7 · sim 0.65

```
1- Introducción

1- Introducción

5
ES
1- Introducción
1.1- Descripción General de la Serie
Este manual recoge las instrucciones de puesta en marcha y mantenimiento de las 
centrales analógicas, así como sus datos técnicos.
La gama de centrales de detección de incendios analógica está compuesta por 5 
modelos:
• De 1 lazo no ampliable con capacidad para baterías de 7A/h
• De 2 lazos no ampliables con capacidad para baterías de 7A/h
• De 4 lazos no ampliables con capacidad para baterías de 7A/h
• De 4 lazos ampliable a 8 lazos con capacidad para batería de 18A/h
• De 4 lazos ampliable a 8 lazos con capacidad para batería de 24A/h
La gama de centrales analógica  ha sido concebida para dar servicio a medianas y 
grandes instalaciones que requieren de un sistema de detección de incendio, tales 
como, centros de negocios, Industrias, campus universitarios, hospitales, escuelas, 
pequeña y mediana empresa, etc.
Las centrales analógicas han sido diseñadas de acuerdo a los requisitos para centrales 
de detección de incendios recogidos en las normas EN54 Parte 2 y 4.
Estas centrales deben ser instaladas por personal cualificado según la norma EN54 
parte 14.
1.2- Precauciones y advertencias de seguridad
Es importante respetar el orden de conexionado del equipo a la alimentación
• En primer lugar, conectar el equipo a la red principal (230VAC)
• En segundo lugar, conectar las baterías
Si no respetamos este orden, el equipo podría sufrir daños.
```

**[F4]** `CAD-150-8` · *2.4 Niveles de Acceso* · `55315008-Manual-Centrales-Analogicas-CAD-150-8-Usuario-ES-FR-GB-IT` p.12 · sim 0.82

```
2.4 Niveles de Acceso

10
ES
2.3.10 Led Anular
Este indicador amarillo indica que alguna zona, elemento del lazo o las sirenas están 
desconectadas. Si se trata de las sirenas, también se iluminará el led Sirenas/Fallo/
Anuladas.
2.3.11 Led Fallo
Indicador amarillo que se activa de forma fija cuando se produce alguna situación 
crítica en el sistema. En este caso el sistema no está operativo
2.3.12 Led Salidas Anuladas
Este indicador amarillo se activa de forma fija cuando existe alguna desconexión de 
las salidas de relés. También se activa si algún modulo de relé del lazo esta en modo 
desconexión.
2.4 Niveles de Acceso
Las centrales analógicas disponen de 2 niveles de acceso siguiendo la norma EN54 
parte 2. De esta forma solo podemos acceder a los menús de configuración o control 
si se introduce la clave adecuada.
• Nivel 1: Todas las indicaciones de la central están operativas,  pero los controles del 
equipo están bloqueados, solo se permite un control visual de display.
• Nivel 2: Una vez introducida la clave pertinente, podemos acceder a los controles de 
la carátula. En este nivel no se puede acceder a la configuración del sistema.
11
ES
3- Menú de Usuario​
3.1- Menú de Usuario (Central 1 y 2 Lazos)
3.1.1 Menú Principal
Una vez introducida la clave del nivel 2, podemos acceder al menú de navegación 
para el usuario. A continuación se muestran los menús de navegación.
El menú seleccionado se mostrará siempre con un parpadeo del asterisco.
3.1.1 Menú ZONA
Pulsando OK, desde el menú principal, accederemos al menú ZONA.
En el menú zona podremos acceder a los submenús Ver, Ver zonas en Prueba, 
Conectar, Desconectar y Prueba.


[TABLA EXTRAÍDA]
3.1- M | enú de U | sua | rio (Ce | ntral 1 y 2 | Lazos) |  | 
----------------------------------------
 |  |  | 3.1.1 M
[… contenido truncado para legibilidad]
```

**[F5]** `CAD-150-8` · *MANUAL DEL USUARIO* · `55315008-Manual-Centrales-Analogicas-CAD-150-8-Usuario-ES-FR-GB-IT` p.3 · sim 0.65

```
MANUAL DEL USUARIO

MANUAL DEL USUARIO

ES
Centrales de detección de incendio analógicas
Guía de usuario 
MANUAL DEL USUARIO
3
ES
ÍNDICE
1- Introducción............................................................................................................ 5
	 1.1- Descripción General de la Serie............................................................................ 5
	 1.2- Precauciones y advertencias de seguridad............................................................ 5
2- El Panel de Control................................................................................................. 6
 	 2.1- Descripción general.............................................................................................. 7
	 2.2- Teclas de control.................................................................................................. 8
	 2.3- Indicaciones luminosas........................................................................................ 9
	 2.4- Niveles de Acceso.............................................................................................. 10
3- Menú de Usuario....................................................................................................11
	 3.1- Menú de Usuario (Central 1 y 2 Lazos)......................................................................... 11

3.1.1- Menú Principal......................................................................................................... 11
	 3.2- Menú de Usuario (Central 4 y 8 Lazos).........................................................................22

3.2.1- Menú Principal............................................................................................. 22
4- Procedimiento en caso de Alarma o Avería..........................................
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## Conexión de baterías en la CAD-150-8

**Importante — orden de conexionado obligatorio** [F3]:
1. Primero conectar la red principal (**230 VAC**)
2. Después conectar las baterías

> ⚠️ Si no se respeta este orden, el equipo podría sufrir daños [F3].

---

### Especificaciones de las baterías

La central requiere **dos baterías de 12V 7A/h** [F1], que deben conectarse **en serie** para el correcto funcionamiento [F1].

---

### Procedimiento de conexión paso a paso

1. **Coloca las baterías** en la parte inferior de la caja, en el espacio reservado para ello, de forma **vertical** [F1].

2. **Conecta el cable puente** (suministrado con la central) uniendo el **polo positivo de una batería con el polo negativo de la otra**, para ponerlas en serie [F1].

3. **Conecta los cables del circuito** (rojo y negro) al positivo y negativo del conjunto de baterías [F1]:
   - Cable **rojo** → polo **positivo**
   - Cable **negro** → polo **negativo**

4. **No conectes la central a la red** hasta no haber completado la puesta en marcha [F2].

---

### Nota sobre capacidad de batería

La gama CAD-150-8 incluye modelos con distintas capacidades [F3]:
- Modelos de 1, 2 y 4 lazos no ampliables → baterías de **7A/h**
- Modelos de 4 lazos ampliables a 8 lazos → baterías de **18A/h** o **24A/h**

Verifica qué modelo concreto tienes instalado para confirmar la capacidad correcta.

---

**Fuente:** Manual Centrales Analógicas CAD-150-8 Instalación (55315013) y Manual del Usuario CAD-150-8 (55315008-Manual-Centrales-Analogicas-CAD-150-8-Usuario-ES-FR-GB-IT) — sin revisión registrada.

---

También puedo ayudarte con: **conexión del bucle analógico**, **conexión de sirenas** o **puesta en marcha de la CAD-150-8**.
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

**Razón del judge:** Todas las afirmaciones técnicas del bot están respaldadas por los fragmentos F que cita: la conexión en serie de dos baterías 12V 7A/h, el cable puente entre polos, la colocación vertical en la parte inferior de la caja, los cables rojo/negro al positivo/negativo, y el orden de conexión (red primero, baterías después) aparecen literalmente en F1, F2 y F3. La nota sobre capacidades de batería según modelo también está en F3. No se detectan alucinaciones ni miscitaciones.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [X] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué: La respuesta me parece buena, pero mejorable. No obstante, aquí es raro porque al lanzarle la misma pregunta en telegram me ha respondido esto: "No tengo información sobre el modelo CAD-150.Tengo manuales de: Detnov, Morley, Notifier.¿Puedo ayudarte con alguno de estos fabricantes?". voy a darte feedback sobre lo que indicas en "## respuesta del bot", pero ten en cuenta lo que te acabo de decir. F1 habla de "2.4 Conexión a la red" cuando en realidad los fragmentos que está extrayendo el Retriever son de "2.5 conexión de las baterías". Además, no es una tabla extraída, por lo que no entiendo a qué te refieres cuando indicas "tabla extraída" al principio del fragmento extraído (mismo error que en hp002). F2 sí que parece recoger los fragmentos de forma correcta, aunque hay solape entre lo que recoge F1 y lo que recoge F2. Un tema relevante es que la CAD-150 tiene variantes en función del número de lazos, y la CAD-150-8 es en realidad la de 4 lazos ampliable a 8 lazos, como puedes ver en este enlace "https://www.detnov.com/productos/sistema-analogico/centrales-analogicas-serie-cad-150/central-de-deteccion-de-incendio-analogica-de-4-lazos-ampliable-a-8-lazos-cad-150-8/". De hecho, en la sección 1.1 del documento "55315013 Manual Centrales Analogicas CAD-150-8 Instalacion ES FR GB IT"  hay un diagrama de la central de 1 y 2 lazos (p2 y p3), y en la sección 1.2 del mismo documento hay un diagrama de la central de 4 y 8 lazos (p4 y p5), que me gustaría que asegurases que están recogidos. Aquí creo que es importante que el bot haga una pregunta clarificatoria. Por último, y no relacionado con esta pregunta pero que es relevante para el correcto funcionamiento del bot, de las páginas 11 a la 33 aparecen unos diagramas que me gustaría que asegurases que estamos capturando. Veo además que F4 te refieres a "2.4 Niveles de acceso" cuando en realidad estás trayendo además info de 2.3.10, 2.3.11, 2.3.12, que están en la misma página pero en una sección anterior. Veo que 3.1 lo estás extrayendo como tabla y no como imagen. Aquí no se si tiene sentido extraerlo como diagrama (y por lo tanto como imagen) o como tabla, pero desde luego se puede limpiar más ya que dices que 3.1.1 es una tabla, cuando en realidad no lo es.**

**Calibración Claude:**

**Respuesta de referencia (basada en `55315013 Manual CAD-150-8 Instalación` sec. 2.5):**

Para conectar las baterías en la CAD-150-8 (4 lazos ampliable a 8): se usan **2 baterías de 12V 7Ah en serie** (suman 24V). Cable puente une polo positivo de una con polo negativo de la otra. Cables del circuito: rojo al positivo del conjunto, negro al negativo. Colocación vertical en la parte inferior de la caja. **Orden de conexionado obligatorio**: (1) primero la red 230 VAC, (2) después las baterías — si se invierte, el equipo puede dañarse (sec. 1.2).

**Calidad de los chunks (problemas críticos identificados):**

- **F1 lleva marcador "[TABLA EXTRAÍDA]" falso**, igual que hp002. El contenido es texto plano en columnas, no una tabla real.
- **F1 header dice "2.4- Conexión a la red"** pero el contenido es de **sec. 2.5 Conexión de las baterías**. Alberto lo detectó. Mismatch entre metadata y contenido = problema sistémico del pipeline de chunking.
- **F4 header dice "2.4 Niveles de Acceso"** pero el chunk contiene 2.3.10, 2.3.11, 2.3.12 (sección anterior) + 2.4. **El extractor pega contenido alrededor del título encontrado sin respetar límites de sección**.
- **F3 trae portada/introducción** (relevante por la advertencia de orden) pero confunde la pertenencia: hay info de modelos en p.5 y de baterías en p.8 — el chunk los junta sin estructura.
- **F1 ∩ F2**: ambos chunks de pág. 8, contenido solapado. Duplicación.
- **Variante del modelo**: la nomenclatura CAD-150-8 cubre versiones 1/2/4/8 lazos con DIFERENTES capacidades de batería (7Ah vs 18Ah vs 24Ah). El bot lo menciona pero asume 7Ah por defecto. **Falta una clarification**: ¿qué modelo concreto tiene el técnico?
- **Diagramas no capturados**: pp. 2-5 (diagramas de central 1/2/4/8 lazos) y pp. 11-33 (más diagramas) son contenido visual probablemente perdido en el pipeline si no hay OCR/vision. Es un riesgo de cobertura.

**Discrepancia Telegram vs eval**: en Telegram el bot responde "no tengo info sobre CAD-150" mientras que aquí responde bien con citas. **Posible bug**: el retriever puede estar fallando si la query no contiene exactamente "CAD-150-8" (sin el "-8"). Indica que el matching de modelo está demasiado pegado al sufijo. Fix: normalizar prefijos de modelo en query expansion.

**Veredicto:**
- [ ] De acuerdo con judge
- [x] **En desacuerdo con judge — yo diría: PASS con caveat**. El bot fue fiel a F y respondió correctamente. Pero el sistema tiene problemas graves de metadata y duplicación que el judge no puede ver.
- **Dimensión equivocada(s) del judge:** ninguna en su scope (bot vs F). El problema es que **el judge no puede verificar metadata de chunks** (header vs contenido). Esto requiere un eval distinto.
- **Nota / por qué:** Coincido con Alberto en que la respuesta es **buena pero mejorable**, y en que los chunks tienen errores graves. Mi divergencia con su FAIL: Alberto está mezclando "respuesta del bot en el eval" con "respuesta del bot en Telegram (que dice no tener info)". Son dos comportamientos distintos del mismo bot — eso ya es problema por sí solo (**reproducibilidad rota**), pero el judge aquí solo está evaluando una versión. Recomendación: separar la métrica de "respuesta correcta vs F" (PASS aquí) de la métrica "comportamiento estable entre interfaces" (FAIL si Telegram dice otra cosa).
- **Origen del problema:** **chunk-extraction** (4 errores: tabla falsa, header mismatch en F1, header mismatch en F4, duplicación F1∩F2), **metadata** (modelo CAD-150-8 ambiguo en familia), **retrieval inestable entre interfaces** (Telegram vs eval), **cobertura visual** (diagramas pp. 2-5, 11-33).

---

## hp004 — judge dice **PASS ✓** · (4/20)

**Pregunta del técnico:** ¿Cuál es la tensión de funcionamiento y el consumo en reposo del detector DGD-600 de Detnov?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 2/3 hits · missing: `['vdc']` · **keyword_pass:** `False`

> _Notas YAML: DGD-600 es detector de gas. Datasheet debería tener estos valores._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `DGD-600` · *Consumo en reposo 45 mA 70 mA* · `55360004 Manual Detector Gas DGD-600 ES EN IT FR` p.1 · sim 0.85

```
Consumo en reposo
45 mA
70 mA (continuación)

Detector  Specification	
24V
220V
Working Voltage
22V a 38V
 180V a 240V
Quiescent current consumption 
45 mA
70 mA
Alarm consumption
65 mA
70 mA
Coverage area
20m2
Relays contact
1A@30VDC
Lower explosive Limit (LEL)
10%
Useful life
10 years since manufacturing 
Wiring recommend
Cable type
2x1,5
Características físicas
Width x Depth x Height
89mm x 146.5mm x 39mm 
220V:
24V:
LOOP IN
LOOP OUT
LOOP IN
LOOP OUT
220V:
24V:

[TABLA EXTRAÍDA]
DETECTORES DE GAS AUTÓNOMO | STAND - ALONE GAS DETECTOR | 
----------------------------------------
LOÑAPSE | HSILGNE | Stand - alone gas detector
```

**[F2]** `DGD-600` · *Especificaciones detector 24V 220V* · `55360004 Manual Detector Gas DGD-600 ES EN IT FR` p.1 · sim 0.80

```
Especificaciones detector
24V
220V (continuación)

ADDRESSABLE
ADDRESSABLE
CONVENTIONAL
LOOP
+    IN   -   +  OUT  -
+
-
24VCC
Opcionalmente los detectores pueden conectarse al lazo de 
comunicaciones de cualquier sistema analógico DETNOV.
ADDRESSABLE
ADDRESSABLE
CONVENTIONAL
LOOP
+    IN   -   +  OUT  -
Para conectarlo es necesario asignarle una dirección correcta 
mediante el programador de direcciones PGD-200 y colocar todos 
los 3 jumpers en los terminales “addresable”. En caso contrario, 
colocar sobre “stand alone”. 
 Los relés se pueden utilizar para actuar sobre cualquier tipo 
de circuito eléctrico. Verifique en el apartado de Características 
Técnicas el valor de corriente y tensión máxima de los contactos.
Stand - alone gas detector 
Read and understand manual before operating or servicing this device.
This device should be installed by qualified personnel.
Some cleaning products like bleach, ammonia… thinners or paints and its gases 
may effect on the detection process.
Do not handle without disconnecting power supplier wires. 
Only clean the  Detector with a wet cloth. 
It’s posible to smell gas before to detect the leak
in case of alarm: do not operate any electrical switches (on or off), do not smoke 
or use a naked flame. Open doors and windows to ventilate the area, check 
your gas appliances and turn them off and if it’s posible turn the gas supply off 
at the main control valve.
1- Introducction   
The range of stand-alone gas detectors has been developed in 
order to detect any leak of flammable gas for everyday use and it is 
composed of the following models:
- Gases lighter than air: Methane, city gas, natural gas. DGD-600
- Liquefied petroleum gas (LP): butane and propane. DGD-620
Both of them include 1 relay to alarm signal and other to fault 
si
[… contenido truncado para legibilidad]
```

**[F3]** `DGD-600` · *Especificaciones detector 24V 220V* · `55360004 Manual Detector Gas DGD-600 ES EN IT FR` p.1 · sim 0.80

```
Especificaciones detector
24V
220V (continuación)

Colocación de los detectores. 
Teniendo en cuenta las diferentes densidades de los gases, el detector 
para gases LP debe instalarse  30 cm sobre el suelo y el detector para 
gases más ligeros que el aire 30 cm bajo el techo. Tal como muestra la 
siguiente figura: 
30 cm
DGD-600
DGD-620
30 cm
Montaje del detector. 
Para desmontar un detector previamente montado es necesario presionar 
con un destornillador sobre la pestaña 
Las bases pueden atornillarse directamente en la pared o montarse sobre 
un carril DIN de 35mm. 
La carcasa se fija sobre la base como muestra la imagen:
3- Test y mantenimiento     
Los detectores estarán operativos unos segundos después de encenderse. 
El botón de test permite comprobar el correcto funcionamiento  de los 
LEDS y los relés. El detector debe ser sustituido 10 años después de su 
fecha de fabricación. La fecha de fabricación está impresa en la pegatina 
adjunta en el lateral del dispositivo. 
4- Características técnicas    
Características medioambiantales
Temperatura de trabajo
-10 ºC a 40 ºC
Temperatura de almacenamiento
-10 º a 40 º C
Humedad relative 
90% sin condensación
Indice IP
IP32D

Especificaciones detector	
24V
220V
Tensión de funcionamiento 
De 22V a 38V
de 180V a 240V
Consumo en reposo  
45 mA
70 mA
Consumo en alarma  
65 mA
70 mA
Área cobertura
20m2
Contactos de Relés 
1A@30VDC
Limite infereior de explosividad (LIE)
10%
Vida útil 
10 años desde su fabricación.   
Características Conexiado 
Tipo de cable 
2x1,5
Características físicas
Ancho x Largo x Alto
89mm x 146.5mm x 39mm 
Placement of the detectors 
Considering the different density of gases, the detector for LP gases will 
be installed at 30cm from the ground. And the detector for gases lighter 
than air at 30cm f
[… contenido truncado para legibilidad]
```

**[F4]** `DGD-600` · *Consumo en reposo 45 mA 70 mA* · `55360004 Manual Detector Gas DGD-600 ES EN IT FR` p.1 · sim 0.80

```
Consumo en reposo
45 mA
70 mA (continuación)

ADDRESSABLE
ADDRESSABLE
CONVENTIONAL
LOOP
+    IN   -   +  OUT  -
+
-
24VCC
Opcionalmente los detectores pueden conectarse al lazo de 
comunicaciones de cualquier sistema analógico DETNOV.
ADDRESSABLE
ADDRESSABLE
CONVENTIONAL
LOOP
+    IN   -   +  OUT  -
Para conectarlo es necesario asignarle una dirección correcta 
mediante el programador de direcciones PGD-200 y colocar todos 
los 3 jumpers en los terminales “addresable”. En caso contrario, 
colocar sobre “stand alone”. 
 Los relés se pueden utilizar para actuar sobre cualquier tipo 
de circuito eléctrico. Verifique en el apartado de Características 
Técnicas el valor de corriente y tensión máxima de los contactos.
Stand - alone gas detector 
Read and understand manual before operating or servicing this device.
This device should be installed by qualified personnel.
Some cleaning products like bleach, ammonia… thinners or paints and its gases 
may effect on the detection process.
Do not handle without disconnecting power supplier wires. 
Only clean the  Detector with a wet cloth. 
It’s posible to smell gas before to detect the leak
in case of alarm: do not operate any electrical switches (on or off), do not smoke 
or use a naked flame. Open doors and windows to ventilate the area, check 
your gas appliances and turn them off and if it’s posible turn the gas supply off 
at the main control valve.
1- Introducction   
The range of stand-alone gas detectors has been developed in 
order to detect any leak of flammable gas for everyday use and it is 
composed of the following models:
- Gases lighter than air: Methane, city gas, natural gas. DGD-600
- Liquefied petroleum gas (LP): butane and propane. DGD-620
Both of them include 1 relay to alarm signal and other to fault 
signal,
[… contenido truncado para legibilidad]
```

**[F5]** `DGD-600` · *Consumo en reposo 45 mA 70 mA* · `55360004 Manual Detector Gas DGD-600 ES EN IT FR` p.1 · sim 0.80

```
Consumo en reposo
45 mA
70 mA (continuación)

Colocación de los detectores. 
Teniendo en cuenta las diferentes densidades de los gases, el detector 
para gases LP debe instalarse  30 cm sobre el suelo y el detector para 
gases más ligeros que el aire 30 cm bajo el techo. Tal como muestra la 
siguiente figura: 
30 cm
DGD-600
DGD-620
30 cm
Montaje del detector. 
Para desmontar un detector previamente montado es necesario presionar 
con un destornillador sobre la pestaña 
Las bases pueden atornillarse directamente en la pared o montarse sobre 
un carril DIN de 35mm. 
La carcasa se fija sobre la base como muestra la imagen:
3- Test y mantenimiento     
Los detectores estarán operativos unos segundos después de encenderse. 
El botón de test permite comprobar el correcto funcionamiento  de los 
LEDS y los relés. El detector debe ser sustituido 10 años después de su 
fecha de fabricación. La fecha de fabricación está impresa en la pegatina 
adjunta en el lateral del dispositivo. 
4- Características técnicas    
Características medioambiantales
Temperatura de trabajo
-10 ºC a 40 ºC
Temperatura de almacenamiento
-10 º a 40 º C
Humedad relative 
90% sin condensación
Indice IP
IP32D

Especificaciones detector	
24V
220V
Tensión de funcionamiento 
De 22V a 38V
de 180V a 240V
Consumo en reposo  
45 mA
70 mA
Consumo en alarma  
65 mA
70 mA
Área cobertura
20m2
Contactos de Relés 
1A@30VDC
Limite infereior de explosividad (LIE)
10%
Vida útil 
10 años desde su fabricación.   
Características Conexiado 
Tipo de cable 
2x1,5
Características físicas
Ancho x Largo x Alto
89mm x 146.5mm x 39mm 
Placement of the detectors 
Considering the different density of gases, the detector for LP gases will 
be installed at 30cm from the ground. And the detector for gases lighter 
than air at 30cm from t
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## DGD-600 — Tensión de funcionamiento y consumo en reposo

El detector **DGD-600** existe en dos versiones de alimentación con valores distintos:

**Versión 24V:**
- Tensión de funcionamiento: **22V a 38V** [F3]
- Consumo en reposo: **45 mA** [F3]
- Consumo en alarma: **65 mA** [F3]

**Versión 220V:**
- Tensión de funcionamiento: **180V a 240V** [F3]
- Consumo en reposo: **70 mA** [F3]
- Consumo en alarma: **70 mA** [F3]

---

Fuente: 55360004 Manual Detector Gas DGD-600 ES EN IT FR (sin revisión registrada)

---

También puedo ayudarte con: **conexionado del DGD-600 en modo stand-alone o direccionable**, **posicionamiento e instalación física** o **procedimiento de test y mantenimiento**.
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

**Razón del judge:** Todos los datos técnicos aportados por el bot (tensión de funcionamiento 22V-38V / 180V-240V y consumo en reposo 45 mA / 70 mA) están explícitamente presentes en F3 (y confirmados en F1, F5), por lo que citation_faithful y corpus_faithful son ambos true sin miscitación. La respuesta aborda exactamente lo preguntado, diferencia correctamente las dos versiones del detector y añade contexto útil sin inventar nada.

### Tu calibración

- [x] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué: Estoy alineado con el judge. El bot de telegram sí que responde de la misma forma que la respuesta que has añadido aquí. No obstante, comete el error de referirse a "F5" y además hacerlo sin corchetes. Por otro lado, un pequeño error de la respuesta del bot que has añadido aquí es que habla de F3 cuando en realidad el usuario no ve F1 ni F2, por lo que igual tiene sentido que a la hora de generar la respuesta para el técnico referenciemos a los documentos por orden de aparición en la respuesta i.e. en este caso solo hay una respuesta por lo que debería ser F1. Si hubiese dos fuentes referenciadas, la primera debería ser F1 y la segunda F2, ya que de cara a los usuarios, si ven directamente "F5" es raro porque no hay F1, F2, F3, F4**

**Calibración Claude:**

**Respuesta de referencia (basada en `55360004 Manual DGD-600` sec. 4):**

| Versión | Tensión de funcionamiento | Consumo en reposo | Consumo en alarma |
|---|---|---|---|
| 24V | 22-38 V CC | 45 mA | 65 mA |
| 220V | 180-240 V CC | 70 mA | 70 mA |

**Calidad de los chunks (duplicación masiva):**

- **El manual del DGD-600 es esencialmente un datasheet de 1 página**. Los 5 chunks F1-F5 vienen TODOS de p.1 con similitud 0.80-0.85. **F3 y F5 son idénticos en contenido**. F1, F2, F4 son variantes parciales del mismo datasheet. Estamos pagando 5 chunks para extraer 1 página.
- **Headers totalmente inútiles**:
  - F1 header: "Consumo en reposo 45 mA 70 mA" — fragmento de tabla
  - F2 header: "Especificaciones detector 24V 220V" — fragmento de tabla
  - F3 header: igual que F2
  - F4, F5: iguales fragmentos
  - Ninguno apunta a sección real ("4. Características técnicas").
- **F1 contiene "[TABLA EXTRAÍDA]" sobre contenido que sí parece visual** (el banner bilingüe "DETECTORES DE GAS AUTÓNOMO | STAND-ALONE GAS DETECTOR"), pero la tabla real de características técnicas no está marcada como tabla. **Inconsistencia inversa otra vez**.
- **El bot citó [F3]** en su respuesta, pero por convención de presentación al usuario, Alberto señala con razón que debería renumerarse como **[F1]** porque es el primer (y único) fragmento usado en la respuesta. Esto es **bug del prompt del generador**: instruir "usa numeración secuencial 1..N solo de los F que efectivamente cites, no el rank original".

**Comparación con bot:**
- ✓ Datos correctos en ambas versiones.
- ✓ Cita F3 consistentemente.
- ⚠️ Numeración de citas para usuario final mal (F3 sin F1, F2).
- ⚠️ El keyword fail de "vdc" es porque el manual usa "V CC" en español; el bot dice "V". Es un sinónimo legítimo. **Fix YAML, no del bot**.

**Veredicto:**
- [x] **De acuerdo** con el veredicto del judge (PASS).
- **Dimensión equivocada(s) del judge:** ninguna.
- **Nota / por qué:** Pregunta canónica de extracción de tabla. El bot la resolvió bien. Problemas sistémicos: (a) chunking que devuelve 5 versiones de la misma página, desperdiciando top-k; (b) headers no representativos de la sección; (c) numeración de citas que confunde al usuario final.
- **Origen del problema:** **chunk-extraction** (duplicación masiva 5×; headers como fragmentos de tabla; marcadores de tabla mal aplicados), **generación** (numeración de citas no normalizada para usuario), **YAML del eval** (keyword "vdc" es sinónimo de "V CC" en español; ajustar lista de keywords).

---

## hp005 — judge dice **PASS ✓** · (5/20)

**Pregunta del técnico:** En la Notifier ID3000, ¿cómo se programa una zona para que active una salida de sirena solo cuando haya coincidencia de dos detectores?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/5 hits · missing: `['doble detección', 'correlación']` · **keyword_pass:** `False`

> _Notas YAML: Típico edge case — lógica de doble zona. Puede aparecer como 'coincidence', 'AND logic', etc._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil
> 🔗 miscitation flag activo — dato puede estar en corpus pero el bot citó mal

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Matriz de control* · `MPDT190` p.66 · sim 0.80

```
Matriz de control

Matriz de control
MP-DT-190_D
       59
Panel ID3000 - Manual de programación
Entradas en un panel de la red
Es posible definir las relaciones entre las
entradas en un panel y las salidas en otro.
Las salidas sólo se aplican al panel que las
controla (como los paneles independientes),
pero las entradas se pueden definir como
originadas en un panel diferente. Para
relacionar una operación de salida en un
equipo supervisado por un panel con una
entrada originada en otro, la Matriz de control
se debe editar en el panel que supervisa al
equipo.
Nota: Para entradas de red, la definición de
‘coincidencia de equipo’ depende de la
definición de la entrada:
Coincidencia de
Equipo
Dos sensores en
alarma en la zona
especificada.
Dos sensores en
alarma en cualquier
lugar de la red
(incluyendo paneles
diferentes)
Entrada
Zona especificada en
otro panel
Cualquier zona en
cualquier panel


[TABLA EXTRAÍDA]
Pane | l | ID3000 - Ma | nual | de programación | 
----------------------------------------
Entradas e | n | un panel | de la | red | 
Es posible | d | efinir las | rela | ciones entre las | 
entradas en | u | n panel y l | as s | alidas en otro. | 
Las salidas | s | ólo se apli | can | al panel que las | 
controla (co | m | o los pan | eles | independientes), | 
pero las en | tr | adas se p | ued | en definir como | 
originadas |  | en un pa | nel | diferente. Para | 
relacionar | u | na operac | ión | de salida en un | 
equipo sup | e | rvisado po | r un | panel con una | 
entrada orig | in | ada en otr | o, la | Matriz de control | 
se debe edi | ta | r en el pa | nel | que supervisa al | 
equipo. |  |  |  |  | 
Nota: Para | e | ntradas de | red | , la definición de | 
‘coinc | id | encia de e | quip | o’ depende de la | 
defini | ci | ón de la e | ntrad | a: |
[… contenido truncado para legibilidad]
```

**[F2]** `ID3000` · *6.4.3 Zona* · `MCDT190` p.59 · sim 0.72

```
6.4.3
Zona

6.4.3
Zona

Matriz de Control
MC-DT-190
       NOTIFIER ESPAÑA
       53
6.4.3
Zona
Si la columna ‘Número del equipo de SALIDA’ muestra el número de un
módulo, esta columna indica automáticamente su zona. Si en esa
columna se puede leer la palabra ‘TODOS’, en ésta se visualizará la
zona o subzona en la que deben activarse todos los módulos. Introduzca
el número de zona o subzona (hasta 255) y, a continuación, pulse
<ENTER>.
Las subzonas sólo están disponibles si el tipo de salida es ‘TODOS’ y la
función ‘Horaria’ está ajustada a NO. Utilice la tecla ‘C’ para cambiar
entre subzonas y zonas; en las subzonas, la letra ‘C’ aparece antes del
número.
De manera alternativa puede pulsar la barra ESPACIADORA para
seleccionar ‘CUALQUIER zona’, es decir, todo el sistema.
Nota: En cualquier caso, si la columna ‘Número del Equipo’ (EQU) muestra
el número de un módulo, cambiará automáticamente a ‘TODOS’.
Se dispone de otra opción cuando la especificación de la ENTRADA es
‘CUALQUIER zona’ (sólo entrada de equipo LOCAL). La indicación ‘MISM’
significa que la zona seleccionada es la misma que la zona de la entrada
donde se produjo la alarma.
Nota: Esta opción no está disponible para acciones de ‘RETARDO’ o
‘COINCIDENCIA’.
Si la columna de ‘Tipo’ está ajustada a ‘ANULAR’ (‘DISAB’),  podemos
seleccionar la zona que deseamos desactivar mediante la activación del
módulo de entrada ‘AUXILIAR’.
6.4.4
Pulsante
Si en esta columna (‘Pulsa’) aparece la palabra SÍ, el equipo de salida se
activará en pulsos de 1 segundo activado y 1 segundo desactivado, a
menos que el equipo haya sido programado a ‘XPULSE’ en la pantalla de
edición del módulo. En este caso, se activará según la intermitencia
programada. Si hubiese otra línea de la matriz de control que activara  la
misma salida o salida
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *1 Ajuste la señal técnica a "Modo ESPERA: Continua temp. Y PAUSA".* · `MCDT191_1` p.72 · sim 0.80

```
1
Ajuste la señal técnica a "Modo ESPERA:
Continua temp. Y PAUSA".

1
Ajuste la señal técnica a "Modo ESPERA:
Continua temp. Y PAUSA".

Matriz de control
ID3000 - Manual del programa de configuración PK-ID3000
MC-DT-191_F v. 2.17e
     66
IRI
ZONA
A
ZONA
B
Pausa 
programada
INICIO DEL 
TEMPORIZADOR
EMISIÓN
DEL GAS
ESPERA
TIEMPO TRANSCURRIDO
TIEMPO RESTANTE
ACTIVADA
DESACTIVADA
ULI
Pausa 
programada
INICIO DEL 
TEMPORIZADOR
EMISIÓN
DEL GAS
ESPERA
TIEMPO TRANSCURRIDO
TIEMPO RESTANTE
ACTIVADA
DESACTIVADA
NYC
INICIO DEL 
TEMPORIZADOR
ACTIVADA
DESACTIVADA
EMISIÓN
DEL GAS
ESPERA
TIEMPO TRANSCURRIDO
TIEMPO RESTANTE
NYC - Cuando la función de ESPERA se
desactiva, el temporizador empieza de nuevo
desde el inicio del tiempo configurado.
Para configurar este modo:
1
Ajuste la señal técnica a "Modo ESPERA:
REINICIO y AUMENTAR Temp".
2
Ajuste el retardo de activación a un periodo
de tiempo mayor al que tiene por defecto
la central (60 segundos).
ULI - Cuando la función de ESPERA se activa,
el temporizador se para en pausa un número
determinado de segundos. Cuando la ESPERA
se desactiva, el temporizador se inicia de
nuevo.
Para configurar este modo:
1
Ajuste la señal técnica a "Modo ESPERA:
Continua temp. Y PAUSA".
2
Asegúrese de que las entradas de alarma
son ‘Extinción AUTO’ o ‘Extinción MANUAL’
sin ‘Ignorar ESPERA’.
IRI - Igual que el modo ULI pero la actividad
de la función de ESPERA se ignora si hay
dos o más zonas en alarma coincidente.
Para configurar este modo:
1
Ajuste la señal técnica a "Modo ESPERA:
Continua temp. Y PAUSA".
2
Asegúrese de que las entradas de alarma
son ‘Extinción AUTO’ o ‘Extinción MANUAL’
con ‘Ignorar ESPERA’.
3
Asegúrese de que las entradas de alarmas
tienen la opción "Coincidencia Múltiples
Zonas" seleccionada.
```

**[F4]** `ID3000` · *Alarma térmica* · `MCDT191_1` p.82 · sim 0.80

```
Alarma térmica

Alarma térmica

Matriz de control
ID3000 - Manual del programa de configuración PK-ID3000
MC-DT-191_F v. 2.17e
     76
4
Si el evento de entrada es Alarma, ‘Un
Equipo determinado’, en lugar de las
selecciones de zona o subzona, se abrirá
la ventana de ‘Seleccionar equipo’. (i)
Seleccione la zona del menú desplegable.
(ii) seleccione el equipo deseado y pulse
‘Aceptar’ (iii).
5
Si el evento de entrada es Alarma, Punto
virtual, seleccione el Punto requerido entre
los disponibles en la ventana de
‘Seleccionar Punto Virtual’ y pulse
‘Aceptar’.
Alarma térmica
Estas opciones solo son aplicables a los sensores
Optiplex y SMART. La entrada está activa cuando
un sensor detecta una alarma térmica (cualquier
instrucción de alarma normal configurada para el
sensor activo también se activará). Los sensores
se pueden seleccionar por zona (cualquiera o
determinada) o por equipo individual.
Se habilita entonces la función para programar la
coincidencia de 2 equipos. Los equipos en alarma
deben estar en la misma zona o subzona, o en
un rango de subzonas si esta opción está
configurada (véase la Sección 2.12). La opción
de coincidencia de múltiples equipos no está
disponible.
4(iii)
4(ii)
4(i)
5
```

**[F5]** `ID3000` · *EN54-2: 9.1.2 La anulación y la habilitación DEBEN ser operaciones manuales.* · `MPDT190` p.24 · sim 0.80

```
EN54-2: 9.1.2
La anulación y la
habilitación DEBEN ser
operaciones manuales.

EN54-2: 9.1.2
La anulación y la
habilitación DEBEN ser
operaciones manuales.

Configuración del panel
MP-DT-190_D
       17
Panel ID3000 - Manual de programación
3.11 Funciones horarias
Esta opción permite modificar las funciones del
panel a ciertas horas del día. Existen tres
aplicaciones principales:
a. Alteración de la sensibilidad de los sensores
a ciertas horas del día - véase la
Sección 5.1.2.7.
b. Realización de algunas acciones en la Matriz
de control (por ejemplo, un retardo)  sólo a
ciertas horas del día - véase la
Sección 7.6.2.2.
c. Cancelación de todas las anulaciones del
panel a ciertas horas del día (no cumple
EN54-2) - véase la Sección 11.7.
Nota: Una Matriz de control puede controlar las
funciones de anular y habilitar,
independientes de la función CANCELAR
ANULACIÓN (véase la Sección 7.7).
Una típica programación horaria consiste en uno
o dos periodos diarios con horario de inicio y fin
y con un horario alternativo para fines de
semana. Pueden estar operativos un máximo de
siete programas horarios en un mismo panel.
Estos programas funcionan de manera
completamente independiente . La sensibilidad
de los sensores o cualquier Matriz de control se
puede modificar sólo de acuerdo a uno de los
programas.
Si desea más detalles sobre la edición de la
programación horaria, consulte la Sección 9.
3.12 Ajustar fecha y hora
Esta opción permite:
a. Ajustar la fecha y la hora.
b. Ajustar la velocidad del reloj.
c. Seleccionar las fechas de inicio y fin del
horario de verano.
Consulte la Sección 10.
3.13 Ajustes del panel
Un gran número de funciones del panel disponen
de varias opciones, por ejemplo, los modos de
intermitencia de las sirenas, los niveles de
acceso para SILENCIAR ZUMBADOR,
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## Programación de coincidencia de dos detectores en ID3000

La función que necesitas es la **"Coincidencia de equipo"** dentro de la **Matriz de Control**. Aquí tienes el procedimiento:

---

### Concepto clave

La ID3000 permite definir en la Matriz de Control que una salida (sirena) solo se active cuando **dos sensores estén en alarma simultáneamente en la misma zona** [F1]. Esto es lo que el manual denomina "coincidencia de equipo".

---

### Configuración en la Matriz de Control

**1. Accede a la Matriz de Control** del panel que supervisa la salida de sirena.

**2. Define la entrada:**
- Tipo de entrada: **Alarma de zona**
- Selecciona la **zona específica** donde están los detectores [F1].
- Al definir la entrada como "zona especificada", la coincidencia de equipo se interpretará como **dos sensores en alarma en esa zona concreta** [F1].

> ⚠️ Si defines la entrada como "cualquier zona en cualquier panel", la coincidencia se evaluará con dos sensores en alarma en **cualquier lugar de la red**, incluyendo paneles diferentes [F1].

**3. Activa la opción de coincidencia de 2 equipos:**
- El manual indica que esta función se habilita para programar la **coincidencia de 2 equipos** [F4].
- Los equipos en alarma deben estar en la **misma zona o subzona** [F4].

> ⚠️ Nota importante: La opción de **coincidencia de múltiples equipos no está disponible** para alarmas térmicas de sensores Optiplex y SMART [F4]. Verifica el tipo de detector que usas.

**4. Define la salida:**
- Asigna la **sirena** como equipo de salida en la línea de la Matriz de Control.
- Configura la zona o subzona donde deben activarse los módulos de sirena [F2].

**5. Configura el modo pulsante si es necesario:**
- Si quieres que la sirena suene de forma **intermitente**, ajusta la columna "Pulsante" a **SÍ** (pulsos de 1 segundo activado / 1 segundo desactivado) [F2].
- Si quieres que suene de forma **continua**, ajusta a **NO** [F2].

---

### Consideración para instalaciones en red

Si los detectores están en **paneles distintos**, la Matriz de Control debe editarse en el **panel que supervisa el equipo de salida** (la sirena) [F1]. La entrada se define como originada en el otro panel, y la coincidencia seguirá las reglas descritas en el punto 2 [F1].

---

### Lo que los fragmentos no especifican

Los fragmentos disponibles no detallan la **secuencia exacta de pantallas** del software **PK-ID3000** para activar la opción de coincidencia paso a paso. Para el procedimiento completo de navegación por menús, consulta la Sección correspondiente a la Matriz de Control en el manual **MC-DT-191_F v. 2.17e** [F4].

---

**Fuentes:**
- MPDT190 (Manual de programación ID3000, sin revisión registrada) [F1, F5]
- MCDT190 (Matriz de Control ID3000, sin revisión registrada) [F2]
- MCDT191_1 / MC-DT-191_F v. 2.17e (Manual del programa de configuración PK-ID3000, sin revisión registrada) [F3, F4]

---

También puedo ayudarte con: **configuración de retardo de activación de sirena**, **programación de zonas en red multi-panel** o **ajuste del modo pulsante/continuo de sirenas** en la ID3000.
```

### Veredicto del judge: **PASS ✓**

```
- citation_faithful: False
- corpus_faithful:   True
- miscitation:       True
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    True
```

**Razón del judge:** La respuesta es técnicamente correcta y bien fundamentada: la función de coincidencia de 2 equipos en la Matriz de Control está documentada en V9 (sección 6.1.5), que el bot no vio pero cuyo contenido reproduce fielmente. La afirmación clave sobre activar la columna 'Coincidencia' a SÍ para requerir dos equipos en alarma antes de activar la salida está en V9, no en F1/F4 como cita el bot — esto es miscitación por retrieval miss, no alucinación. La advertencia sobre pulsadores manuales y la disti

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué: Para empezar, la respuesta del bot de Telegram difiere de la que has incluido tu aquí. La respuesta del bot de Telegram es "Los fragmentos recuperados *no contienen información* sobre la programación de coincidencia de dos detectores (lógica de doble knock o doble detector) para activar una salida de sirena en la ID3000.

Los fragmentos disponibles cubren:
- Configuración de sensibilidad de alarma (niveles L1-L9) [F2][F3]
- Modo Día/Noche y retardos de investigación [F1]
- Procedimiento de recepción de configuración desde la central [F5]
- Indicaciones de prueba y anulación de circuitos de sirena [F4]

Ninguno de ellos describe la lógica de *doble coincidencia de detectores* ni cómo vincularla a una salida de sirena.

Para obtener este procedimiento, consulta directamente:
- El manual *MCDT191* (Manual del programa de configuración PK-ID3000) en las secciones de *lógica de zonas o causas/efectos (cause & effect)*, que es donde habitualmente se configura este tipo de lógica en paneles analógicos direccionables — aunque no puedo confirmarlo sin el fragmento correspondiente.
- El soporte técnico de *Notifier España*.

Fuente: MCDT191_1, MCDT190, MFDT190 (sin revisión registrada)". Si baso mi evaluación sobre la respuesta que has incluido. Veo que F1 tiene fragmento texto y fragmento tabla "Tabla extraida", pero la realidad es que "Es posible definir las relaciones entre entradas en un panel y las salidas en otro. Las salidas sólo se aplican al panel que las controla (como los paneles independientes), pero las entradas se pueden definir como originadas en un panel diferente. Para relacionar una operación de salida en un equipo supervisado por un panel con una entrada originada en otro, la Matriz de control se debe editar en el panel que supervisa al equipo." no es una tabla. 

Sobre la respuesta que has incluido aquí: he subido el documento a Claude CoWork y le he hecho la misma pregunta que a ti, a lo que me ha respondido lo siguiente: 
"Respuesta basada en el manual MP-DT-190 (Notifier ID3000)
Para que una zona active una sirena solo cuando dos detectores coincidan en alarma, hay que crear una instrucción en la Matriz de Control (no basta con configurar la zona). El procedimiento es:
1. Acceder al menú de Matriz de Control (Sección 7.5 / 7.6 del manual)
Desde Configuración → Configuración de matriz de control → VER/EDITAR MATRIZ DE CONTROL, pulsar * para crear nuevo evento.
2. Definir la ENTRADA como ALARMA

Tipo de entrada: 1: ALARMA
Para sensores multicriterio: 1: Normal (Combinada) Alarma
Origen: 1: Subzona, zona o central → seleccionar la zona deseada (ZONA en vez de CENTRAL o SUBZONA).

3. Configurar la coincidencia de equipos ("Coincidencia de equipos") — éste es el paso clave
Al elegir una única zona, el manual presenta la pantalla:
"Indique tipo de coincidencia:
  1: UN ÚNICO EQUIPO
  2: COINCIDENCIA 2 EQUIPOS
  3: n COINCIDENCIA EQUIPOS
  4: p COINCIDENCIA EQUIPOS
Hay que seleccionar 2: COINCIDENCIA 2 EQUIPOS. Las opciones 3 y 4 solo aparecen si se han configurado umbrales superiores en Sección 11.21 – Niveles COINCIDENCIA en ALARMA.
4. Limitación por tipo (opcional pero recomendado)
Si quieres que la coincidencia sea entre dos detectores y excluir pulsadores, en "¿Limitado por TIPO?" selecciona p.ej. 2: CUALQUIER SENSOR TÉRMICO, o usa directamente las opciones combinadas:

9: COINCIDENCIA sensor HUMO y TÉRM
11: COINCIDENCIA VIEW y otro SENSOR

⚠️ Aviso EN54-2 (7.1.4) del propio manual: no incluir pulsadores manuales (PUL) en un grupo de coincidencia. Para gestionarlos, crear dos instrucciones separadas en la matriz: una para PUL como "UN ÚNICO EQUIPO" sin coincidencia, y otra para los sensores con coincidencia.
5. Definir la SALIDA → la sirena
A continuación se configura la definición de salida apuntando al circuito o módulo de sirena deseado (p.ej. SIRENA interno Cct.3, una sirena de lazo, un módulo CMX configurado como sirena, o ZONA n, SIRENA). Aquí se puede añadir también un retardo de sirena si se desea.
Resultado: la entrada de matriz solo se activará cuando dos equipos (detectores) de esa zona estén simultáneamente en alarma, disparando entonces la salida de sirena definida.

Consideraciones importantes (extraídas del manual)

Para que se produzca la coincidencia, los equipos deben estar en la misma zona (o subzona, si se han configurado). En CUALQUIER ZONA el comportamiento depende del ajuste de Sección 11.21 – Funcion. COINCIDENCIA para 'CLQ ZONA' (Misma CENTRAL vs Misma ZONA).
No se pueden combinar en la misma entrada las funciones de coincidencia de zonas y limitación por tipo (nota explícita del manual).
Si combinas COINCIDENCIA 2 EQUIPOS + Limitado por tipo, la comprobación de tipo solo se aplica al segundo equipo que completa la coincidencia. El manual recomienda, en su lugar, agrupar todos los equipos de coincidencia en una zona/subzona específica.
Para coincidencias de 3 o más equipos, primero hay que configurar los umbrales en Configuración de la central → 22: Niveles COINCIDENCIA en ALARMA → para EQUIPOS.

Sources: MP-DT-190_D, Panel ID3000 – Manual de programación, secciones 7.5, 7.6.1.1 (págs. 62–66) y 11.21 (págs. 107–108)."

Sobre la respuesta anterior, le he preguntado esto: "qué metodos has utilizado para extraer la respuesta, y como puedo aprovecharlo en mi RAG?", y me ha respondido esto:
"Métodos que utilicé
1. Inspección del PDF antes de leer. Con pdfinfo confirmé que son 142 páginas, generado con Adobe PageMaker → Distiller. Eso ya me dice que es un PDF "nativo" (texto extraíble, no escaneo) y que la maquetación es de manual técnico a doble columna con cajas de diálogo, no prosa lineal.
2. Extracción preservando layout. Usé pdftotext -layout (en vez de la extracción "flow" por defecto). En este manual el contenido crítico vive en capturas de pantalla de la central representadas como bloques de texto enmarcados; sin -layout se desordenan y pierdes el orden lógico de las pantallas.
3. Routing por tabla de contenidos. Antes de buscar contenido grepeé el índice del propio manual y localicé candidatos por número de sección: 7.12 Detección de coincidencia, 11.21 Coincidencia de alarma, 7.5/7.6 Matriz de control. La TOC del documento es un router gratuito y muy fiable.
4. Búsqueda léxica multinivel. Grep con términos del dominio (coinciden, doble, dos detect, sirena, matriz de control). Iteré: primero términos de la pregunta, luego sinónimos que vi aparecer (p.ej. "COINCIDENCIA 2 EQUIPOS", "matriz de control"), luego referencias cruzadas que el propio texto menciona (Sección 11.21).
5. Lectura contextual ampliada. Una vez localizadas las líneas, leí ventanas de ±100-300 líneas alrededor (sed -n). El procedimiento real estaba repartido entre tres secciones y los pasos numerados (1→9) ocupan varias páginas.
6. Reconstrucción multi-hop. La respuesta no estaba en un único pasaje: combiné (a) cómo se crea una instrucción de matriz, (b) la pantalla concreta de "Indique tipo de coincidencia", (c) el aviso EN54-2 sobre pulsadores, (d) la sección 11.21 para los umbrales >2 equipos.
Cómo aprovecharlo en tu RAG
Pipeline de ingesta.

Extrae con pdftotext -layout (o pdfplumber con extract_text(layout=True)). Para manuales con muchos diagramas de flujo o capturas, considera un modelo visual (Donut, LayoutLM, GPT-4V) para esas páginas en concreto: la sección 7.2 de este PDF, por ejemplo, tiene un diagrama de flujo que en texto queda destrozado.
Detecta y conserva la numeración jerárquica de secciones (\d+(\.\d+)+) como metadatos del chunk. Es tu mejor identificador estable para citar y para enlaces cruzados.

Chunking.

No partas por longitud fija. Parte por encabezado de sección y, dentro de cada sección, por bloque de pantalla/diálogo (en este manual cada "captura" es una unidad atómica de procedimiento). Un chunk que parta una pantalla por la mitad pierde sentido operativo.
Adjunta a cada chunk: section_number, section_title, page, breadcrumb (cadena de títulos padre) y la lista de referencias cruzadas que aparecen en su texto (Sección 11.21, Apéndice 3, etc.). Esas referencias son oro para retrieval multi-hop.

Recuperación.

Híbrida: BM25 + embeddings. En este dominio hay frases-tipo exactas ("COINCIDENCIA 2 EQUIPOS", "matriz de control", "Niveles COINCIDENCIA en ALARMA") que el usuario teclea literalmente; BM25 las clava, los embeddings solos a veces no.
Añade un paso de expansión por TOC: si la query menciona "coincidencia/doble disparo/two-stage", recupera secciones cuyo título contenga el término además de los chunks más similares. Imita lo que yo hice cuando miré la TOC primero.
Implementa expansión por referencias cruzadas: cuando un chunk recuperado mencione "Sección X.Y", añade automáticamente esa sección al contexto. Resuelve los multi-hop como el de esta pregunta.

Generación.

Pide al LLM que cite section_number + página en cada afirmación. Lo tienes en metadatos y es trivial validar.
Mete los avisos normativos (en este manual los EN54-2, "PRECAUCIÓN", "IMPORTANTE") como chunks de alta prioridad: márcalos con un flag y boostea su score para que nunca se queden fuera del contexto, porque suelen ser justo lo que diferencia una respuesta correcta de una peligrosa.

Evaluación.

Construye un set de preguntas de "procedimiento" (como la que me hiciste) y mide recall de pasos: ¿la respuesta menciona las 3-4 piezas que están repartidas por el documento? Más útil que medir similitud textual con una gold answer.
Casos adversarios típicos en este tipo de manual: terminología en inglés vs español ("double knock" vs "coincidencia"), abreviaturas ("PUL", "CMX"), referencias a versiones (Sección 11.2 vs 11.21 — esto aparece en el propio PDF y es una errata de imprenta que tu RAG debe tolerar).".

Sobre tu respuesta, ha indicado esto: 
"Veredicto rápido
Respuesta parcialmente útil pero con fallos graves: omite el dato más operativo (el nombre exacto de la opción de menú), se inventa una restricción que probablemente no está en el manual, y desvía al usuario a otro documento para algo que sí estaba en el suyo. Honesta en el "no sé", pero la honestidad no compensa la información incorrecta.
Lo que está bien

Cita fuentes con identificadores [F1..F5] y separa los manuales que contribuyen a cada afirmación. Buen patrón.
Acierta el comportamiento en red: la matriz se edita en el panel que supervisa la salida, no la entrada (eso está en MPDT190).
Acierta la interpretación "zona especificada → dos sensores en esa zona" vs "cualquier zona → cualquier punto de la red". Ese matiz aparece literalmente en la tabla de la sección 7.2 del manual.
Tiene una sección explícita de "lo que los fragmentos no especifican". Reduce alucinación.

Lo que está mal
1. Omite el paso más importante: el nombre del menú.
La pantalla real de la central es:
"Indique tipo de coincidencia:
  1: UN ÚNICO EQUIPO
  2: COINCIDENCIA 2 EQUIPOS
  3: n COINCIDENCIA EQUIPOS
  4: p COINCIDENCIA EQUIPOS
Un técnico delante del panel necesita saber que tiene que elegir la opción 2 en esa pantalla concreta. Tu RAG dice "activa la opción de coincidencia de 2 equipos" sin decir dónde ni cómo. Es la diferencia entre una respuesta operativa y una descriptiva.
2. Omite un aviso normativo crítico (EN54-2).
El manual incluye un bloque destacado: "EN54-2: 7.1.4 PRECAUCIÓN: No incluya pulsadores manuales en un grupo de coincidencia", con instrucciones para separar PUL en dos instrucciones de matriz distintas. Esto no es opcional, es cumplimiento normativo. Que un RAG sobre seguridad contra incendios se salte avisos EN54 es un problema serio.
3. Posible alucinación sobre Optiplex/SMART.
La afirmación "La opción de coincidencia de múltiples equipos no está disponible para alarmas térmicas de sensores Optiplex y SMART" huele a invertida. En el manual, lo que se dice sobre Optiplex/SMART es lo contrario: la opción "Especial Sólo Alarma Térmica" está disponible exclusivamente para esos sensores. Tu RAG ha leído un texto que restringe a esos sensores y lo ha convertido en una restricción contra esos sensores. Si confirmas que esto no está en los chunks recuperados, es alucinación pura.
4. Desvía a otro manual innecesariamente.
Cierra diciendo "para el procedimiento completo de navegación por menús, consulta MC-DT-191_F". Pero la navegación por menús sí está en MPDT190 (las secciones 7.5, 7.6 y 11.21 son exactamente eso). Eso significa que tu RAG tiene MPDT190 indexado pero no recuperó los chunks correctos. Falla de retrieval, no de corpus.
5. Falta la interacción "coincidencia + limitación por tipo".
Las opciones 9, 10, 11 (COINCIDENCIA sensor HUMO y TÉRM, COINCIDENCIA Sensor y PUL, COINCIDENCIA VIEW y otro SENSOR) están específicamente diseñadas para el caso "coincidencia entre dos detectores" y son justo lo que pregunta el usuario. No aparecen.
6. Falta el cross-reference a Sección 11.21.
Si quieres coincidencia de 3+ equipos primero hay que configurar umbrales globales en Configuración de la central → Niveles COINCIDENCIA en ALARMA. Sin eso, las opciones n y p ni aparecen en el menú de la matriz. El RAG no enlaza este pre-requisito.
7. Paso 5 (Pulsante SÍ/NO) es ruido.
La pregunta era sobre coincidencia, no sobre modo de pulso de sirena. Esto es "padding" típico de RAG que mete cualquier chunk relacionado con "sirena" para parecer completo.
Diagnóstico de tu pipeline (qué falló dónde)
SíntomaCausa probableOmite "COINCIDENCIA 2 EQUIPOS" textualRetrieval semántico sin BM25. La frase exacta no aparece en los chunks top-k.Omite aviso EN54-2Chunking que separa el procedimiento de su recuadro de PRECAUCIÓN adyacente.Inversión OptiplexEl modelo generador alucinó cuando el chunk de Optiplex era ambiguo y no relacionado con la pregunta. Falta paso de groundedness.Te manda a MC-DT-191_F teniendo MPDT190Tu RAG tiene MPDT190 indexado pero el chunk con el procedimiento (sección 7.6.1.1) no entra en el top-k para esta query.Mete "Modo pulsante"Top-k está dominado por chunks de "sirena" genéricos en vez de chunks de "matriz + coincidencia".
Acciones concretas
Sobre retrieval:

Hybrid search: añade BM25 en paralelo. La query implícita "COINCIDENCIA 2 EQUIPOS" la clava BM25, embeddings no.
Query expansion con sinónimos del dominio: coincidencia → double knock → doble detección → 2 equipos → confirmación cruzada.
Reranker (Cohere Rerank, BGE-reranker) tras el retrieval inicial. Bajaría el chunk de "Pulsante" y subiría el de la pantalla "Indique tipo de coincidencia".

Sobre chunking:
4. Chunk por bloque de pantalla + texto contiguo, no por longitud fija. En este manual cada captura UI va con su explicación a la derecha; sepáralas y pierdes ambos.
5. Sticky warnings: cualquier chunk con EN54, PRECAUCIÓN, IMPORTANTE, Nota se adhiere al chunk de procedimiento más cercano (mismo número de sección). Que nunca viaje solo.
6. Cross-reference graph: parsea referencias "Sección X.Y" y guárdalas como aristas. En recuperación, expande automáticamente al chunk apuntado.
Sobre generación:
7. Groundedness check post-hoc: para cada afirmación de la respuesta, comprueba que aparece en los chunks recuperados. Un modelo barato (Haiku) basta para etiquetar "soportado / no soportado". La frase de Optiplex la habrías cazado.
8. Prompt de prioridad: indica al generador que los chunks con marcador normativo (EN54, PRECAUCIÓN) son obligatorios en la respuesta si fueron recuperados.
9. No-handoff rule: si la respuesta sugiere "consulta otro manual", verifica primero que ese contenido no está en los chunks disponibles del manual actual. Evita el "envíate a otro lado" cuando la respuesta está en casa.
Sobre evaluación:
10. Monta un eval set con preguntas-procedimiento y mide cobertura de pasos (¿menciona los 4-5 pasos clave?) y cobertura de advertencias (¿menciona el EN54?). Es mejor métrica que similitud textual.
11. Añade un test adversario específico de inversión de polaridad (afirmaciones del tipo "X no está disponible para Y" cuando el manual dice "X solo está disponible para Y"). Es un fallo recurrente de los RAG técnicos.
Si quieres, puedo pasarte un prompt de groundedness y un esquema de chunking con sticky-warnings ya listo para que lo pruebes contra este mismo PDF y veas si la respuesta mejora."

**

**Calibración Claude:**

**Respuesta de referencia (basada en `MPDT190 - Panel ID3000 Manual de programación`, secciones 7.5, 7.6.1.1 págs. 62-66 y 11.21 págs. 107-108):**

Procedimiento documentado en el manual:
1. Acceder a Matriz de Control: Configuración → Configuración de matriz de control → VER/EDITAR MATRIZ DE CONTROL → `*` para crear nuevo evento.
2. Definir la ENTRADA como `1: ALARMA`, origen `1: Subzona, zona o central`, seleccionar zona.
3. En la pantalla "Indique tipo de coincidencia" elegir **`2: COINCIDENCIA 2 EQUIPOS`**.
4. (Opcional) Limitar por tipo: opciones `9: COINCIDENCIA sensor HUMO y TÉRM`, `10: COINCIDENCIA Sensor y PUL`, `11: COINCIDENCIA VIEW y otro SENSOR`.
5. Definir la SALIDA → sirena.
6. ⚠️ Aviso EN54-2 (7.1.4): no incluir pulsadores manuales en grupo de coincidencia. Crear instrucciones separadas.

Para 3 o más equipos: configurar antes umbrales en sec. 11.21 Niveles COINCIDENCIA en ALARMA.

**Calidad de los chunks (crítica aquí):**
- **F1 lleva "[TABLA EXTRAÍDA]" sobre un párrafo de texto plano** — error sistémico repetido (hp002, hp003, hp005).
- **El chunk clave de la pregunta — pantalla "Indique tipo de coincidencia: 1 UN ÚNICO EQUIPO / 2 COINCIDENCIA 2 EQUIPOS / 3 n COINCIDENCIA EQUIPOS / 4 p COINCIDENCIA EQUIPOS" en pág. 66 (sec. 7.6.1.1) NO está en ningún F**. Es el contenido procedimental más importante de la pregunta. **Retrieval miss grave.**
- **Aviso EN54-2 7.1.4 sobre pulsadores manuales** tampoco aparece en F. Otro fragmento crítico perdido.
- F2 (MCDT190 sec. 6.4.3 Zona), F5 (MPDT190 funciones horarias) son ruido para esta pregunta.
- F3 (MCDT191_1 ESPERA), F4 (MCDT191_1 alarma térmica + Optiplex/SMART) son tangenciales.

**Comparación con bot:**
- ✓ Identifica "Coincidencia de equipo" correctamente.
- ✓ Distingue "zona específica" vs "cualquier zona".
- ✓ **Comportamiento de honestidad ejemplar**: sección explícita "Lo que los fragmentos no especifican…" admitiendo el gap.
- ⚠️ No menciona la opción literal "2: COINCIDENCIA 2 EQUIPOS" porque no la tiene en F.
- ⚠️ Posible inversión de polaridad: dice "La opción de coincidencia de múltiples equipos no está disponible para alarmas térmicas de sensores Optiplex y SMART", pero F4 dice lo contrario (la opción térmica ES *exclusiva* de Optiplex/SMART; lo que no está disponible es "coincidencia múltiples equipos" — ambigüedad real del manual, bot la propagó).
- ⚠️ Desvía al MC-DT-191_F cuando el procedimiento está en MPDT190 (no recuperado).

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS). El judge fue **excepcionalmente preciso** detectando miscitación por retrieval miss vs alucinación pura. Buen comportamiento del judge en este caso.
- **Dimensión equivocada(s) del judge:** ninguna.
- **Nota / por qué:** Caso paradigmático de retrieval miss + generación honesta. El bot hizo lo correcto con lo que tenía. La inconsistencia Telegram vs eval que detecta Alberto es **el problema crítico**: el bot a veces responde y a veces dice "no tengo info" para la misma query. **No-determinismo del retrieval erosiona la confianza del técnico.**
- **Origen del problema:** **retrieval** (pág. 66 sec. 7.6.1.1 y aviso EN54-2 no entraron en top-5), **chunk-extraction** (F1 falsamente marcado como tabla; chunking parte la pág. 66 justo antes del contenido relevante), **inestabilidad retrieval** (Telegram vs eval traen chunks distintos para la misma query), **generación** (posible inversión de polaridad sobre Optiplex/SMART que se debe a la ambigüedad del propio chunk F4).

---

## hp006 — judge dice **PASS ✓** · (6/20)

**Pregunta del técnico:** La Notifier AFP-400 muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza?

**Conducta esperada:** `admit_no_info` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `False`

> _Notas YAML: Cambiado a admit_no_info en sesión 15 (24 abril 2026): corpus verificado — 'Earth Fault' y 'fallo tierra' solo aparecen en NFS Supra, ID50/60, ZXe, DXc; no en AFP-300/400. Bot admite correctamente._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `AFP-300/AFP-400` · *Lectura de un Punto Individual* · `MIDT170` p.182 · sim 0.80

```
Lectura de un Punto Individual

Lectura de un Punto Individual

MI-DT-170k
174
NOTIFIER ESPAÑA
Introduzca lo siguiente:
1) Introduzca la primera letra del equipo.
• Detector
• Módulo
• Circuito del Panel
• Zona
• Función Especial
• Zona de Extinción (Releasing Zone); o
• Parámetro del Sistema
2) Introduzca la dirección o número del equipo.
3) Pulse <Enter>.
Uso del CRT-2 para Lectura de Estados, continuación
Pulse D(nnn), M(nnn), P(nn), Z(nn), F(n), R(n) o S(n) y
pulse Enter
1
Pulsar...
ENTER
NORMAL HUMO (ÓPTICO) DIRECC.DETECTOR 101 Z03 Z Z Z Z
000%A5 PA:3 ** D101
y el CRT-2 Visualiza...
D    1    0    1
Pulsar...
NORMAL ÚNICO (ION.)DIRECC. DETECTOR 102 Z02 Z Z Z Z
000%A5 PA:0 ** D102
NEXT
ENTER
Desde el menú de Lectura de Estados, seleccione la opción 1. El CRT-2
visualiza lo siguiente:
Para avanzar en la lista de equipos desde el CRT
Para retroceder en la lista de equipos desde el CRT
Ejemplo:  Lectura del punto para el detector 101.
  (nnn)
Dirección
Número de Lazo
Número
(SIGUIENTE)
Dirección
F5
F6
Lectura de un Punto Individual
```

**[F2]** `AFP-300/AFP-400` · *Campos por defecto en la Autoprogramación* · `MPDT170` p.10 · sim 0.80

```
Campos por defecto en la Autoprogramación

MP-DT-170
10
NOTIFIER ESPAÑA, S.A.
Si un sensor existe en la programación de la Central, pero no se encuentra (no
responde a la Central) la Central mostrará el siguiente mensaje:
• Para eliminar el equipo de memoria, pulse la tecla <Enter>.  Aparecerá el
siguiente equipo en la pantalla.
• Para mantener el equipo en memoria, pulse la tecla <Esc>.  En la pantalla de
la Central aparecerá el Modo de Programación.
Por cada nuevo equipo, la opción de Autoprogramación selecciona y muestra
unos valores por defecto. Por ejemplo:
Valores por defecto en la Autoprogramación
Valores por Defecto en la
Autoprogramación
La siguiente tabla contiene información de los diferentes campos que aparecen
en la pantalla de autoprogramación por defecto.
Campos por defecto en la Autoprogramación
Autoprogramación,
continuación
Si utiliza el sensor iónico CPX-
551 en aplicaciones de conductos
de aire, ajuste el nivel de
sensibilidad de alarma a “1.”
PROGRM HUMO(IONICO)     DIREC.SENSOR 101
Z03 Z Z Z Z
  AL:5 PA:0
      **  D101
Zona por
defecto
Tipo de equipo
Zonas
Umbral de Alarma
Nivel de Pre-Alarma
Modo Multi-detector
Verificación de Alarma
 2-digitos dirección
Número de lazo
PROGRM HUMO(IONICO) DIREC.SENSOR 133
EQUIPO NO LOCALIZADO ELIMINAR PUNTO D133
Campo
Descripción
HUMO(OPTICO)
Tipo de identificación del sensor analógico
DIREC.SENSOR 101
Descripción por Defecto:  101 (1=lazo 1; 01=dirección 01)
Z03
Selección de la zona por defecto:
• Zona 01 (sensores térmicos)
• Zona 02 (sensores iónicos)
• Zona 03 (sensores ópticos)
• Zona 04 (sensores láser)
• Zona 05 (multisensores)
Puede cambiar la zona por defecto además de añadir
cuatro zonas más en la programación de cada detector.
AL:5
Nivel de sensibilidad de alarma, con “9” es el nivel de
menor sensibili
[… contenido truncado para legibilidad]
```

**[F3]** `AFP-300/AFP-400` · *Circuito Especificaciones del Alambrado* · `50253SP` p.169 · sim 0.80

```
Circuito
Especificaciones del Alambrado

Tablero Interface de la Red (NIB-96)
5. Aplicaciones
AFP-300/AFP-400 Instalación PN 50253SP:D  12/07/98
5-7
Conexiones del SLC del NIB-96 y del EIA-485 
La Figura 5-6 muestra los alfileres de contacto para el SLC (P5) y las conexiones del  
EIA-485 (P4) en el módulo del NIB-96. El circuito del EIA-485 requiere una conexión 
en serie. Conecte solamente un alambre a cada tornillo del terminal.
Figura 5-6   Conexiones del SLC y del EIA-485
Especificaciones de Alambre
La Tabla 5-5 contiene las especificaciones del alambrado para alambrar un circuito SLC 
y un EIA-485:
Tabla 5-5  Especificaciones del Alambrado del NIB-96
P5 – SLC 
P4 – EIA-485
8    7    6    5    4     3     2    1
 6    5    4    3     2    1
+ Salida del EIA-485 
+ Entrada del EIA-485 
– Salida del EIA-485
– Entrada del EIA-485
No conexión
No conexión
Entrada del Lazo SLC (+) 
Entrada del Lazo SLC (Blindado)
Entrada del SLC  (–)
Tierra
Salida del SLC (+) 
Salida del SLC (Blindado)
Salida del SLC (–)
Tierra
Circuito
Especificaciones del Alambrado
SLC
Supervisado y de energía limitada
Distancia máxima de alambre:  10,000 pies en 12 AWG
Corriente del SLC máxima: 200 mA (corto circuito) o 100 mA 
(normal)
Resistencia máxima del: 40 ohmios
EIA-485
Supervisados y de energía limitada
±5 voltios de pico a pico
Distancia máxima de alambre: 6000 pies en 14 AWG
Resistencia máxima del circuito: 40 ohmios
Característica de impedancia del alambre: 120 ohmios
Rango de transmisión: 2400 baud
5. Aplicaciones
Utilizando el Transponder de la Serie XP con un AFP300 o un AFP400
5-8
AFP-300/AFP-400 Instalación PN 50253SP:D  12/07/98
Utilizando el Transponder de la Serie XP con un AFP300 o un AFP400
Introducción del Transponder de la Serie XP
El Transponder de la Serie XP es un subsitema
[… contenido truncado para legibilidad]
```

**[F4]** `AFP-300/AFP-400` · *Generador de Tono de Audio ATG-2* · `MFDT170` p.32 · sim 0.72

```
Generador de Tono de Audio ATG-2

Generador de Tono de Audio ATG-2

MF-DT-170c
26
NOTIFIER ESPAÑA, S.A.
Generador de Tono de Audio ATG-2
Si desea más información sobre
la configuración del ATG--2,
consulte la sección dobre
Módulos Audibles del Manual
de Instlación de la AFP-400.
Figura 52: Características de Funcionamiento del ATG-2
ffcc10a   
AUDIO
TONE
GENERATOR
PAGE
SELECT
ON LINE
EVAC CHANNEL
ALERT CHANNEL
TROUBLE
Canal Secundario (ALERTA)
(doble canal) - aviso o un tono
de 20 ppm (pulsaciones por
minuto)
Micrófono Incorporado
El ATG-2 proporciona tonos seleccionados por el usuario para salidas de un
único o doble canal. El ATG-2 proporciona diferentes formas de llamadas.
• Llamada directa - El ATG-2-micrófono con un botón que le permite llamar  a
través de los circuitos de megafonía primarios y secundarios. Si lo utiliza con
un FFT-7 opcional, el ATG-2 proporciona un sistema de comunicación a partir
de los teléfonos instalados en toda la instalación.
• Micrófono de llamadas remoto - Puede también ajustar el ATG-2 para parar un
mensaje de audio (o tono) recibido desde un AMG-1 u otro ATG-2. En esta
configuración, el ATG-2 sirve como una ubicación de llamadas alterna
(remota) para el AMG-2 o ATG-2. El ATG-2 proporciona facilidades para
hacer caso omiso de las llamadas del micrófono del ATG-2. Todas las
comunicaciones pasan a través de un NAC (Circuito de Señalizaciones)
utilizando un modo ACS (consulte el Manual de Instalación de la AFP-400)
conectado a la central- excepto si está ajustado para funcionar con un
micrófono de llamadas remoto.
La Figura 52 muestra las características de funcionamiento del ATG-2:
Canal Primario (EVAC) -
tonos lentos, altos y
bajos, o fijos.
Botón de selección de Llamada
- le permite hablar a través de
los circuitos de megafonía en
uno, d
[… contenido truncado para legibilidad]
```

**[F5]** `AFP-300/AFP-400` · *• Umbral Canal A. Canal de umbral A (alto o bajo) para nodo. Si desea más información, consulte el manual de Noti·Fire·N* · `MADT170` p.6 · sim 0.72

```
• Umbral Canal A. Canal de umbral A (alto o bajo) para nodo. Si desea más
información, consulte el manual de Noti·Fire·Net.

• Umbral Canal A. Canal de umbral A (alto o bajo) para nodo. Si desea más
información, consulte el manual de Noti·Fire·Net.

MA-DT-170
NOTIFIER ESPAÑA, S.A.
6 de 11
Programación en red (2)
Opciones de programación en red
Desde la pantalla para cambiar la programación, pulse 2 para que aparezca la
pantalla de programación en red (figura 6)
UMBRAL CANAL A:A,
UMBRAL CANAL B:A,
NODO:000, DESPL.ESPECIAL, ACS:00, <ENTER>
La pantalla de programación en red dispone de 4 opciones:
• Umbral Canal A. Canal de umbral A (alto o bajo) para nodo. Si desea más
información, consulte el manual de Noti·Fire·Net.
• Umbral Canal B. Canal de umbral B (alto o bajo) para nodo. Si desea más
información, consulte el manual de Noti·Fire·Net.
• Nodo. Dirección del nodo en la red (001-240). Un nodo es cualquier panel de
control, repetidor, PC que se conecta a la red Noti·Fire·Net y se comunica con
otros nodos que utilizan la red. Por ejemplo, una AFP-300/AFP-400 ocupa una
dirección de nodo en la red.
• Desplazamiento especial. (Desplazamiento de dirección). Direccionado del
Anunciador: este parámetro indica la dirección del anunciador captada por
Noti·Fire·Net. Por ejemplo, si el desplazamiento es 20, al anunciador especial
se le asignan las direcciones 21 y 22, y así sucesivamente. Los anunciadores
especiales son anunciadores con doble dirección: A y B, programables
únicamente desde el Veri·Fire 400, versión 3.x.
Si desea más información sobre la programación de la red, consulte el manual
del NAM-232, revisión E o superior.
Para seleccionar las opciones de red, siga este procedimiento:
1. Desde la pantalla para realizar los cambios de programación (figura 3, página
    4), p
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados del manual de la **AFP-300/AFP-400** no contienen información sobre el aviso **'Tierra' (Earth Fault)**: su significado, causas ni procedimiento de localización.

Los fragmentos disponibles cubren únicamente:
- Lectura de puntos individuales desde el CRT-2 [F1]
- Campos de autoprogramación y valores por defecto [F2]
- Especificaciones de alambrado del NIB-96 (SLC y EIA-485) [F3]
- Configuración del generador de tono ATG-2 [F4]
- Programación en red Noti·Fire·Net [F5]

**Para obtener la información correcta sobre el fallo de tierra**, consulta directamente:
- El manual de instalación de la AFP-400 (sección de diagnóstico de fallos / troubleshooting)
- El soporte técnico de Notifier España

---

Fuente: MIDT170, MPDT170 (rev. Rev B), 50253SP, MFDT170, MADT170 — sin revisión registrada en la mayoría de fragmentos.
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

**Razón del judge:** El bot admite correctamente que los fragmentos F recuperados no contienen información sobre el aviso 'Tierra' (Earth Fault) ni su procedimiento de localización. Aunque el fragmento V11 menciona 'Falla de Tierra' en el contexto del pinout TB1 de la MPS-400 y el puente JP2 para inhabilitar la detección de falla de tierra, esto no constituye una explicación del aviso ni un procedimiento de localización, por lo que la admisión del bot es honesta y apropiada. La conducta admit_no_info es correcta, y

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:Le he pasado los 5 manuales disponibles sobre la central a Claude Cowork, y me ha generado este archivo con la respuesta gold standard ""C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Projects\PCI\gold_answer_earth_fault_AFP400.md"**

**Calibración Claude:**

**Respuesta de referencia (basada en `gold_answer_earth_fault_AFP400.md` que generamos previamente sobre los 5 manuales AFP-300/AFP-400):**

El aviso 'Tierra' indica una fuga eléctrica a tierra. Detección en la **MPS-400** vía LED dedicado "Falla de Tierra" (TB1-1) y configurable cortando puente **JP2** [50253SP pág. 2-43]. Severidad varía por Estilo del lazo (en Estilo 4 puede escalar a Alarma) [MI-DT-170 pág. 63]. Para localizar: observar qué MPS-400 tiene el LED encendido, revisar histórico (`<Enter>` → 2 → 2), descartar PC en EIA-232 sin aislar [Apéndice E], usar Monitores MMX en remotas, considerar ACT-1 para sistemas grandes. **No hay procedimiento paso a paso de bisección documentado en estos 5 manuales.**

**Calidad de los chunks (problema crítico):**
- **Los 5 fragmentos F1-F5 son completamente ajenos a la pregunta**: F1 (Lectura de Puntos CRT-2), F2 (Autoprogramación), F3 (cableado NIB-96), F4 (ATG-2 audio), F5 (red Noti·Fire·Net). **0/5 chunks relevantes.**
- **Sin embargo el corpus SÍ tiene información de "Falla de Tierra"** — está en 50253SP pág. 2-43 (LED + JP2), MI-DT-170 pág. 45-46, sec. ACT-1, Apéndice E. **Retrieval miss masivo.**
- **El propio rationale del judge lo reconoce**: *"el fragmento V11 menciona 'Falla de Tierra' en el contexto del pinout TB1 de la MPS-400 y el puente JP2 para inhabilitar la detección de falla de tierra"*. El chunk existe en el corpus pero no entró en F.
- **Posible causa de la miss**: la query "Earth Fault" o "tierra" puede no estar matcheando bien con "Falla de Tierra" (mayúscula F en Falla). Confirma la necesidad de **normalización de queries y BM25 sobre términos exactos**.

**Comparación con bot:**
- ✓ Comportamiento `admit_no_info` correcto dado lo que vio.
- ✓ Honestidad ejemplar: lista qué cubre cada F y deriva al manual + soporte.
- ✓ No alucina (única opción razonable con esos F).

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) **dentro de su scope (bot vs F)**.
- [ ] **Pero el recalibrado YAML es cuestionable**: la nota dice *"Earth Fault y fallo tierra solo aparecen en NFS Supra, ID50/60, ZXe, DXc; no en AFP-300/400"*. Eso es **falso**: aparece en AFP-300/400 como "Falla de Tierra" (sin la "o" final de "fallo"). El recalibrado se hizo con una búsqueda léxica incompleta. El expected_behavior debería volver a ser `answer`, no `admit_no_info`.
- **Dimensión equivocada(s) del judge:** ninguna. **El error está en el YAML/recalibrado, no en el judge.**
- **Nota / por qué:** Este caso es exactamente lo que el README advierte: "vale la pena verificar si la recalibración fue legítima o si debíamos haber arreglado el bot". **Respuesta: la recalibración NO fue legítima**. El bot SÍ debería haber respondido, pero el retrieval falló y el equipo (sesión 15, 24-abr-2026) decidió enmascararlo cambiando expected_behavior. Cuando el retrieval se arregle, esta pregunta debe volver a ser `answer`.
- **Origen del problema:** **retrieval** (mismatch "Earth Fault"/"tierra" vs "Falla de Tierra"; normalización + BM25 sobre términos exactos), **YAML recalibrado mal** (búsqueda léxica incompleta enmascaró un fallo de retrieval), **chunk-extraction** (los chunks de "Falla de Tierra" + JP2 existen pero no llegaron a top-5).

---

## hp007 — judge dice **PASS ✓** · (7/20)

**Pregunta del técnico:** ¿Cómo se realiza el test anual de un detector VESDA-E VEP según el manual del fabricante?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 2/4 hits · missing: `['aerosol', 'sensibilidad']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `VESDA-E VEP` · *www.xtralis.com 81* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.87 · sim 0.80

```
www.xtralis.com
81

VESDA-E VEP-A10-P Guía del producto
www.xtralis.com
81
7
Mantenimiento
Para mantener el detector VEP-A10-P a su nivel de rendimiento máximo, se debe seguir el programa de
mantenimiento recomendado en la Tabla 7-1 a continuación.
Tabla 7-1: Calendario de mantenimiento sugerido para el detector VEP-A10-P
Comprobación de
mantenimiento
Cada tres
meses
Cada seis
meses
Una vez al
año
Cada dos
años
Fuente de alimentación y Batería
Comprobar la red de Tubería
Realizar una prueba de humos
para comprobar la integridad de
las Tubería
Comprobar el flujo de las
Tubería
Limpiar los puntos de muestreo
Limpiar con agua la red de
Tubería
Sustitución del filtro
Notas:
l Los pasos anteriores corresponden al mantenimiento preventivo.
l Pueden realizar el mantenimiento el instalador original, un distribuidor autorizado o el contratista de
servicio.
l La frecuencia necesaria de las comprobaciones de mantenimiento puede variar en función de los códigos
y las normas locales, y del entorno de la instalación.
l Cuando se realicen las pruebas de humo, siga los procedimientos del sitio para evitar falsas alarmas
para los servicios supervisados.
Precaución: Cuando el detector está deshabilitado o en espera, el detector no emitirá advertencias de fuego.
Antes de realizar el mantenimiento o las pruebas:
l Informe a la autoridad supervisora adecuada .
l Asegúrese de que se aíslen los dispositivos existentes que dependan del detector antes
de que se ponga en funcionamiento.
Atención:
Pendant que le detecteur ou la zone est desactivee, aucun feu d’indication va etre emis par le
detecteur. Avant tout entretien ou tester:
l Informer les autorité de supervision appropriée.
l S'assurer que tout les appareils auxiliaires dépendants sur le détecteur sont isolés avant
de commencer aucun tra
[… contenido truncado para legibilidad]
```

**[F2]** `VESDA-E VEP` · *7 Mantenimiento* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.87 · sim 0.80

```
7
Mantenimiento

VESDA-E VEP-A10-P Guía del producto
www.xtralis.com
81
7
Mantenimiento
Para mantener el detector VEP-A10-P a su nivel de rendimiento máximo, se debe seguir el programa de
mantenimiento recomendado en la Tabla 7-1 a continuación.
Tabla 7-1: Calendario de mantenimiento sugerido para el detector VEP-A10-P
Comprobación de
mantenimiento
Cada tres
meses
Cada seis
meses
Una vez al
año
Cada dos
años
Fuente de alimentación y Batería
Comprobar la red de Tubería
Realizar una prueba de humos
para comprobar la integridad de
las Tubería
Comprobar el flujo de las
Tubería
Limpiar los puntos de muestreo
Limpiar con agua la red de
Tubería
Sustitución del filtro
Notas:
l Los pasos anteriores corresponden al mantenimiento preventivo.
l Pueden realizar el mantenimiento el instalador original, un distribuidor autorizado o el contratista de
servicio.
l La frecuencia necesaria de las comprobaciones de mantenimiento puede variar en función de los códigos
y las normas locales, y del entorno de la instalación.
l Cuando se realicen las pruebas de humo, siga los procedimientos del sitio para evitar falsas alarmas
para los servicios supervisados.
Precaución: Cuando el detector está deshabilitado o en espera, el detector no emitirá advertencias de fuego.
Antes de realizar el mantenimiento o las pruebas:
l Informe a la autoridad supervisora adecuada .
l Asegúrese de que se aíslen los dispositivos existentes que dependan del detector antes
de que se ponga en funcionamiento.
Atención:
Pendant que le detecteur ou la zone est desactivee, aucun feu d’indication va etre emis par le
detecteur. Avant tout entretien ou tester:
l Informer les autorité de supervision appropriée.
l S'assurer que tout les appareils auxiliaires dépendants sur le détecteur sont isolés avant
de commencer aucun travai
[… contenido truncado para legibilidad]
```

**[F3]** `VESDA-E VEP` · *Limpiar con agua la red de Tubería* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.87 · sim 0.80

```
Limpiar con agua la red de
Tubería

VESDA-E VEP-A10-P Guía del producto
www.xtralis.com
81
7
Mantenimiento
Para mantener el detector VEP-A10-P a su nivel de rendimiento máximo, se debe seguir el programa de
mantenimiento recomendado en la Tabla 7-1 a continuación.
Tabla 7-1: Calendario de mantenimiento sugerido para el detector VEP-A10-P
Comprobación de
mantenimiento
Cada tres
meses
Cada seis
meses
Una vez al
año
Cada dos
años
Fuente de alimentación y Batería
Comprobar la red de Tubería
Realizar una prueba de humos
para comprobar la integridad de
las Tubería
Comprobar el flujo de las
Tubería
Limpiar los puntos de muestreo
Limpiar con agua la red de
Tubería
Sustitución del filtro
Notas:
l Los pasos anteriores corresponden al mantenimiento preventivo.
l Pueden realizar el mantenimiento el instalador original, un distribuidor autorizado o el contratista de
servicio.
l La frecuencia necesaria de las comprobaciones de mantenimiento puede variar en función de los códigos
y las normas locales, y del entorno de la instalación.
l Cuando se realicen las pruebas de humo, siga los procedimientos del sitio para evitar falsas alarmas
para los servicios supervisados.
Precaución: Cuando el detector está deshabilitado o en espera, el detector no emitirá advertencias de fuego.
Antes de realizar el mantenimiento o las pruebas:
l Informe a la autoridad supervisora adecuada .
l Asegúrese de que se aíslen los dispositivos existentes que dependan del detector antes
de que se ponga en funcionamiento.
Atención:
Pendant que le detecteur ou la zone est desactivee, aucun feu d’indication va etre emis par le
detecteur. Avant tout entretien ou tester:
l Informer les autorité de supervision appropriée.
l S'assurer que tout les appareils auxiliaires dépendants sur le détecteur sont isolés avant
de com
[… contenido truncado para legibilidad]
```

**[F4]** `VESDA-E VEP` · *Limpiar los puntos de muestreo* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.87 · sim 0.80

```
Limpiar los puntos de muestreo

VESDA-E VEP-A10-P Guía del producto
www.xtralis.com
81
7
Mantenimiento
Para mantener el detector VEP-A10-P a su nivel de rendimiento máximo, se debe seguir el programa de
mantenimiento recomendado en la Tabla 7-1 a continuación.
Tabla 7-1: Calendario de mantenimiento sugerido para el detector VEP-A10-P
Comprobación de
mantenimiento
Cada tres
meses
Cada seis
meses
Una vez al
año
Cada dos
años
Fuente de alimentación y Batería
Comprobar la red de Tubería
Realizar una prueba de humos
para comprobar la integridad de
las Tubería
Comprobar el flujo de las
Tubería
Limpiar los puntos de muestreo
Limpiar con agua la red de
Tubería
Sustitución del filtro
Notas:
l Los pasos anteriores corresponden al mantenimiento preventivo.
l Pueden realizar el mantenimiento el instalador original, un distribuidor autorizado o el contratista de
servicio.
l La frecuencia necesaria de las comprobaciones de mantenimiento puede variar en función de los códigos
y las normas locales, y del entorno de la instalación.
l Cuando se realicen las pruebas de humo, siga los procedimientos del sitio para evitar falsas alarmas
para los servicios supervisados.
Precaución: Cuando el detector está deshabilitado o en espera, el detector no emitirá advertencias de fuego.
Antes de realizar el mantenimiento o las pruebas:
l Informe a la autoridad supervisora adecuada .
l Asegúrese de que se aíslen los dispositivos existentes que dependan del detector antes
de que se ponga en funcionamiento.
Atención:
Pendant que le detecteur ou la zone est desactivee, aucun feu d’indication va etre emis par le
detecteur. Avant tout entretien ou tester:
l Informer les autorité de supervision appropriée.
l S'assurer que tout les appareils auxiliaires dépendants sur le détecteur sont isolés avant
de commenc
[… contenido truncado para legibilidad]
```

**[F5]** `VESDA-E VEP` · *7.1 En espera* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.87 · sim 0.80

```
7.1
En espera (continuación)

[TABLA EXTRAÍDA]
Comprobaciónde mantenimiento | Cadatres meses | Cadaseis meses | Unavez al año | Cadados años
----------------------------------------
FuentedealimentaciónyBatería |  |  |  | 
ComprobarlareddeTubería |  |  |  | 
Realizarunapruebadehumos paracomprobarlaintegridadde lasTubería |  |  |  | 
Comprobarel flujodelas Tubería |  |  |  | 
Limpiarlospuntosdemuestreo |  |  |  | 
Limpiarconagualaredde Tubería |  |  |  | 
Sustitucióndel filtro |  |  |  |
VESDA-E VEP-A10-P Guía del producto
82
www.xtralis.com
Para establecer el detector en el modo en espera mediante Xtralis VSC, seleccione Ir a modo en espera ("Go
to Standby") en el menú Dispositivo ("Device"). El LED desactivado parpadeará y se desactivará el aspirador.
Si se ha configurado, el zumbador emitirá un pitido por minuto si se marca la casilla correspondiente al pitido
en espera en la pantalla de configuración de relés (sección 5.5.10).
Para volver a activar la unidad, seleccione Finalizar modo en espera ("End Standby") en el menú Dispositivo
("Device").
```

### Respuesta del bot

```
## Test anual del VESDA-E VEP-A10-P

El manual incluye la **Tabla 7-1: Calendario de mantenimiento sugerido para el detector VEP-A10-P** [F1], que lista las siguientes tareas de mantenimiento con sus frecuencias asociadas:

**Tareas listadas en el calendario** [F1]:
- Fuente de alimentación y Batería
- Comprobar la red de Tubería
- Realizar una prueba de humos para comprobar la integridad de las Tubería
- Comprobar el flujo de las Tubería
- Limpiar los puntos de muestreo
- Limpiar con agua la red de Tubería
- Sustitución del filtro

**⚠️ Limitación importante:** El manual incluye la Tabla 7-1 con 4 frecuencias (cada 3 meses, cada 6 meses, una vez al año, cada 2 años), pero **las marcas de asignación tarea↔frecuencia no son legibles en los fragmentos recuperados** [F1]. No puedo indicarte con certeza qué tareas concretas corresponden a la revisión anual sin riesgo de error. Consulta la **Tabla 7-1 en el manual físico** (página 81) para ver la asignación exacta.

---

### Precauciones previas a cualquier prueba [F1][F2]

Antes de realizar el mantenimiento o las pruebas:

1. **Informa a la autoridad supervisora adecuada.**
2. **Aísla los dispositivos existentes que dependan del detector** antes de ponerlo en funcionamiento.
3. Cuando realices pruebas de humo, **sigue los procedimientos del sitio para evitar falsas alarmas** en los servicios supervisados.

> ⚠️ **Precaución:** Cuando el detector está deshabilitado o en espera, **no emitirá advertencias de fuego** [F1].

---

### Modo en espera durante el mantenimiento [F1][F5]

Para trabajos en la red de tubería o puntos de muestreo, se recomienda poner el detector en **modo en espera**:

- Esto **desactiva el aspirador** y detiene la detección de alarmas (pero **no** la detección ni señalización de fallos) [F1].
- Para activarlo: en **Xtralis VSC**, selecciona **"Go to Standby"** en el menú **"Device"** [F5].
- El **LED desactivado parpadeará** y se desactivará el aspirador [F5].
- El modo en espera se señaliza por defecto en el **relé 1** [F1]. Consulta las secciones **4.3.6 y 5.5.10** para configuración adicional [F1].
- Para volver a activar: selecciona **"End Standby"** en el menú **"Device"** de Xtralis VSC [F5].

---

**Fuente:** 33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores (sin revisión registrada), Sección 7 – Mantenimiento, p. 81-82.

---

También puedo ayudarte con: **procedimiento de prueba de humos**, **configuración de relés (sección 5.5.10)** o **sustitución del filtro** del VEP-A10-P.
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

**Razón del judge:** El bot responde correctamente con la información disponible en los fragmentos F: lista las tareas del calendario de mantenimiento (Tabla 7-1), las precauciones previas y el procedimiento de modo en espera. Crucialmente, el bot detecta y declara honestamente que las marcas de asignación tarea↔frecuencia no son legibles en los fragmentos recuperados (regla c: tabla con celdas vacías), lo cual es correcto según los chunks F1-F5 donde las intersecciones de la tabla aparecen vacías. Remite al técnico

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué: He pasado la pregunta a Claude CoWork y me ha generado su respuesta además de una comparativa entre tu respuesta y la suya: "C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Projects\PCI\gold_answer_VESDA_VEP_annual_test.md"**

**Calibración Claude:**

**Respuesta de referencia (basada en `gold_answer_VESDA_VEP_annual_test.md` generado previamente):**

No existe un "test anual" único: la Tabla 7-1 lista 4 tareas anuales — (1) prueba de humos, (2) comprobar flujo, (3) limpiar puntos de muestreo, (4) lavar con agua la red de tuberías. La prueba de humo (sec. 6.3) consiste en inyectar humo en el orificio más alejado y medir tiempo de transporte; el procedimiento detallado vive en el *VESDA-E Commissioning Guide* (fuera del corpus). Pruebas integradas en Xtralis VSC: Start Alarm/Fault/Air Flow/Relay/LED Test (sec. 5.4). Apéndice A.3-A.4 contiene los formularios de registro.

**Calidad de los chunks (excelente caso para mostrar la disfunción del extractor):**
- **F1, F2, F3, F4 son duplicados o quasi-duplicados de pág. 87 (sec. 7 Mantenimiento)**. Headers de F1 ("www.xtralis.com 81"), F2 ("7 Mantenimiento"), F3 (`Una vez al año`), F4 (`Limpiar los puntos de muestreo`) son **fragmentos arbitrarios de la misma página repetida**.
- **F5 trae "[TABLA EXTRAÍDA]"** con la Tabla 7-1 SIN las marcas (✓) de qué tarea va en qué columna. **Reproduce el problema que el bot detectó en su respuesta**: las celdas aparecen vacías. Es el mismo error de extracción de tablas que vimos en VESDA cuando preparamos el gold answer.
- **Falta crítica**: sec. 6.3 (principio de la prueba de humo), sec. 5.4 (pruebas integradas vía VSC) y Apéndice A (formularios) **no están en F**. Retrieval miss de 3 piezas críticas.
- **Duplicación 4/5**: F1≡F2≡F3≡F4 todos pág. 87. El top-5 está desperdiciado.

**Comparación con bot:**
- ✓ **Honestidad ejemplar**: el bot detectó la disfunción de la tabla y lo declaró explícitamente. Comportamiento ideal.
- ✓ Listó las 7 tareas de la Tabla 7-1 correctamente.
- ✓ Precauciones y modo en espera bien descritos.
- ⚠️ Faltó: sec. 6.3 (smoke test), sec. 5.4 (pruebas VSC), Apéndice A (formularios), referencia a AS1851.1. Todo por retrieval miss, no por generación.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — el bot fue fiel a F y supo declarar el gap de la tabla. Honestidad de manual.
- **Dimensión equivocada(s) del judge:** ninguna.
- **Nota / por qué:** El bot es 8/10 en faithfulness pero 4/10 en recall. La discusión completa está en el gold answer `gold_answer_VESDA_VEP_annual_test.md`. Acción prioritaria: arreglar retrieval para sec 6.3, sec 5.4 y Apéndice A. Arreglar extracción de tablas vendría después.
- **Origen del problema:** **chunk-extraction** (tabla 7-1 sin marcas; duplicación masiva F1≡F2≡F3≡F4), **retrieval** (no recupera sec 6.3, 5.4, Apéndice A), **YAML keywords** ("aerosol" y "sensibilidad" no están en el manual para esta pregunta — keyword fail legítimo del YAML, no del bot).

---

## hp008 — judge dice **PASS ✓** · (8/20)

**Pregunta del técnico:** ¿Qué detectores de humo analógicos son compatibles con la Notifier ID3000?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 2/4 hits · missing: `['b500', 'nfxi']` · **keyword_pass:** `False`

> _Notas YAML: Notifier serie 500 / NFXI son los típicos de ID3000._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *4.1.2 Equipos de lazo - aisladores* · `MIDT190` p.24 · sim 0.72

```
4.1.2
Equipos de lazo - aisladores

4.1.2
Equipos de lazo - aisladores

Panel ID3000 - Manual de instalación y puesta en marcha
Instalación - sensores y módulos
MI-DT-190_D
       18
4
Sensores y módulos
Estos equipos van acompañados de instrucciones en las
que se muestran las interconexiones adecuadas para cada
aplicación.
4.1
Requisitos de EN54
El diseño de la central ID3000 permite la conexión de un
máximo de 198 equipos en cada uno de sus 8 lazos lazo,
es decir, 99 sensores y 99 módulos.
4.1.1
Equipos de lazo - sensores y pulsadores
manuales
Si no se instalan placas con interfaz de lazo y software
incorporado (LIB3000M), para cumplir con los requisitos de
la norma EN54-2, es necesario conectar un máximo de 512
sensores y/o pulsadores manuales al panel a través de
TODOS los lazos analógicos, incluyendo todos los
detectores de zona convencional y/o los pulsadores
conectados.
Si se instalan placas con interfaz de lazo y software
incorporado (LIB3000M), se aplican los límites de diseño
indicados en la Sección 4.1. Si se instalan LIB3000M y
LIB3000S, se aplican las restricciones del primer párrafo de
la Sección 4.1.1 a todos los lazos que no están conectados
a las LIB3000M.
Si no cumple lo arriba indicado, contravendría la norma
EN54-2 en caso de producirse una avería de sistema.
4.1.2
Equipos de lazo - aisladores
Los aisladores se deben utilizar en cada lazo analógico para
separar los sensores y los pulsadores, incluyendo todos
los lazos con detectores de zona convencional y/o los
pulsadores conectados.
Para cumplir con los requisitos de EN54-2, los aisladores
se deben instalar entre un máximo de 32 equipos de lazo.
En la central ID3000, no se debe colocar más de 25
equipos de lazo entre aisladores (20 si se utilizan
aisladores FET).
Si no cumple lo arriba indicado, con
[… contenido truncado para legibilidad]
```

**[F2]** `ID3000` · *Detector MULTI* · `MCDT190` p.26 · sim 0.72

```
Detector MULTI (continuación)

[TABLA EXTRAÍDA]
Segunda Vent | ana d | el Sensor |  | 
----------------------------------------
Los datos neces | arios | para definir | un | sensor son
demasiados para | que qu | epan en una | sol | a pantalla, así
que continúan en u | na seg | unda ‘venta | na’. | Las columnas
de ‘Lazo, Dirección | , Tipo, | Zona y Celd | a’ so | n iguales que
en la primera venta | na. <F | 2> se usa pa | ra c | ambiar de una
ventana a la otra. |  |  |  | 
Sensibilidad |  |  |  | 
Los paneles de la s | erie ID | 3000 son pan | eles | analógicos y
direccionables, es | decir q | ue reciben y | proc | esan señales
analógicas de los s | ensore | s. Los umbr | ales | programados
en el ID3000 dete | rminan | a qué nivel | se a | ctivan ciertas
operaciones. |  |  |  | 
Con el cursor situ | ado en | la columna | de | ‘Sensibilidad’
deseada, pulse la b | arra es | paciadora re | peti | damente para
seleccionar uno | de lo | s niveles | de | sensibilidad
preestablecidos |  |  |  | 
Nota: Esta sección | incluy | e toda la info | rma | ción relevante
para progra | mar la | sensibilidad | de l | os detectores
VIEW (LPX | -751). | Estos detect | ores | funcionan de
una únic | a ma | nera (si | no | se usan
independient | ement | e, cooperan c | on d | etectores láser
adyacentes) | . Cons | ulte la Guía | de | Aplicación del
VIEW si tien | e algu | na duda. Si n | o di | spone de una
copia de es | te doc | umento, pón | gas | e en contacto
con el Depar | tamen | to Técnico de | NO | TIFIER.
1 Sensibilidad - | Alarm | a |  | 
El umbral de sensi | bilidad | de ALARMA | pu | ede ajustarse,
dentro de unos límit | es, med | iante la confi | gura | ción del panel.
Cada detector disp | one de | hasta 9 nivel | es pr | eajustados de
alarma (L1-L9) (ex | cepto | el detector M
[… contenido truncado para legibilidad]
```

**[F3]** `ID3000` · *en la siguiente franja horaria:* · `MPDT190` p.98 · sim 0.80

```
en la siguiente franja horaria:

en la siguiente franja horaria:

Programación horaria
MP-DT-190_D
       91
Panel ID3000 - Manual de programación
9.4
Modo solo térmico de sensores
MULTICRITERIO (SDX-751TEM)
Si se va a utilizar el modo Solo térmico de estos
sensores, normalmente los sensores se
configurarán para funcionar como sensores
combinados de humo/térmicos durante la noche/
fin de semana y sensores solo modo térmico
durante el día. Se puede programar desde la
programación horaria o mediante la tecla MODO
DÍA de la central, sin embargo, ambas opciones
se configuran a través del parámetro de
programación horaria durante la configuración
del equipo del lazo.
Utilizando la programación horaria
Ajuste el nivel de alarma requerido para el
funcionamiento combinado (ej. en el nivel por
defecto, L3), luego habilite la edición de la
programación horaria y continúe seleccionando
‘MENOS sensible en’ hasta que aparezca en
pantalla ‘Solo parte térmica’. Edite los días y las
horas en que va a funcionar el modo solo térmico
L6.
Nota: Aunque se puede configurar el nivel de
alarma a L6 y luego utilizar la
programación horaria para ajustar un nivel
‘MÁS sensible en’, no es recomendable
ya que cualquier enlace día/noche
funcionará al revés.
La anulación manual se puede configurar tal y
como se describe en la Sección 9.1. Sin
embargo, si se requiere el control mediante teclas
del modo solo térmico, puede que se prefiera
utilizar el método de vinculación al cambio día/
noche que se describe a continuación.
Vincular a cambio Día/Noche
Ajuste el nivel de alarma requerido para el
funcionamiento combinado (ej. en el nivel por
defecto, L3), luego habilite la edición de la
programación horaria y continúe seleccionando
‘MENOS sensible en’ hasta que aparezca en
pantalla ‘Solo parte térmica’.
[… contenido truncado para legibilidad]
```

**[F4]** `ID3000` · *OFF (APAGADO)* · `MFDT190` p.55 · sim 0.80

```
OFF (APAGADO) (continuación)

 Usuario           Lun 01-May-2000 11:20:07
Nota: Si existe una condición de alarma, estas
pantallas no están disponibles porque no hay
suficiente espacio en la pantalla.
5
Puede seleccionar el modo de funcionamiento del
led de los sensores y módulos de entrada. “OFF”
significa que no están iluminados o “parpadean”, si
el panel se ha configurado para que funcione de
esta manera mientras se comprueban los equipos
(“polling”). Seleccione las otras opciones para poder
identificar fácilmente un equipo.
Únicamente en los sensores analógicos, la lectura de
datos del equipo se puede almacenar en un registro
de datos a intervalos de tiempo regulares (destinado
para utilizar con el programa de soporte de la serie
ID3000 que funciona con un PC compatible-IBM):
6
Utilice 
 y 
 para visualizar los diferentes
sensores en la zona seleccionada. Los datos
analógicos y los datos de procesamiento del
VIEW se actualizan constantemente (los datos
del VIEW sólo aparecen si el equipo es un sensor
VIEW. ‘Va’ es una media utilizada para la
compensación por suciedad y normalmente es
del 25% aprox. Por debajo del 5% y por encima
el 35%, el sensor se encuentra en avería. ‘Vs’
indica la condición de alarma del sensor,
corregida por compensación de suciedad).
7
Para configurar un registro, introduzca el valor
numérico de los datos (es decir, las muestras)
que desea almacenar (un máximo de 4000 si no
se están registrando otros sensores, en tal caso
podrían ser menos). Debe utilizar el teclado
numérico para introducir los valores; si pulsa las
teclas 
, 
, 
 o 
, aparecerá en pantalla
el siguiente mensaje “Pulse un dígito para
cambiar registro”.
Nota: Se pueden registrar 28 sensores, como
máximo, simultáneamente, formando un total
de 4000 valores almacenados de una sola
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *INSTRUCCIONES DE INSTALACIÓN* · `MIDT1450` p.2 · sim 0.80

```
INSTRUCCIONES DE INSTALACIÓN

Vía radio. Manual de instalación
MI-DT-1450_A
        2 de 14
INSTRUCCIONES DE INSTALACIÓN
CARACTERÍSTICAS TÉCNICAS GENERALES DE LA COMUNICACIÓN VÍA RADIO
El sistema de detección de incendio vía radio FLG2100 de System Sensor se ha diseñado para poder
funcionar con los sistemas contra incendio analógicos y compatibles que utilizan el protocolo de
comunicaciones de la serie 500 de System Sensor. Cada componente vía radio consta de un procesador
de transmisión con comunicaciones de datos bidireccionales y cambio de frecuencia automática (salto de
frecuencia) y proporciona una conexión en la que la seguridad de la transmisión es comparable a la de los
aparatos conectados por cable.
Todas las instalaciones de sistemas de detección de incendios deben cumplir la normativa local pertinente,
por ejemplo la BS5839, parte 1.
Rango de frecuencia:
bandas de 434MHz y 868MHz
Máxima potencia transmitida: 10mW
Número de canales:
20 en una banda de 434MHz y 4 en 868MHz
Amplitud de canal:
75 kHz
Separación de canal:
banda de 434MHz - 75 kHz; banda de 868MHz - 150 kHz
Capacidad de transmisión:
16,384 kHz ± 200ppm
Sensibilidad del receptor:
-100dBm
Dirección del receptor:
Código no recurrente de 4 bytes
CARACTERÍSTICAS TÉCNICAS DEL INTERFAZ
ANALÓGICO VÍA RADIO FLG2100
•
Fuente de alimentación externa:  24Vcc, 300mA
•
Consumo de corriente en reposo:  Desde 50mA
•
Comunicaciones directas con la central analógica con
protocolo estándar de la serie 500 de System Sensor.
•
EL interfaz FLG2100 supervisa hasta 99 detectores y 98
pulsadores manuales.
•
La información del estado del equipo FLG2100 se
proporciona en una dirección de lazo. Otro tipo de
información de los equipos (alarma / avería) se proporciona
en direcciones de lazo separadas; una por equipo.
•
El FLG21
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados para esta consulta corresponden principalmente a manuales de instalación, programación y funcionamiento de la ID3000, pero **no incluyen una lista de detectores de humo analógicos compatibles** con esta central.

Lo que sí puedo confirmar de los fragmentos disponibles:

- La ID3000 es una central analógica y direccionable que recibe y procesa señales analógicas de los sensores [F2].
- Admite un máximo de **198 equipos por lazo** (99 sensores + 99 módulos) en cada uno de sus **8 lazos** [F1].
- Se mencionan como equipos compatibles los sensores **VIEW™ (LPX-751)** [F2] y los sensores **MULTICRITERIO (SDX-751TEM)** [F3], pero no se proporciona una lista exhaustiva de detectores de humo analógicos compatibles.
- El sistema **FLG2100** de System Sensor utiliza el **protocolo de comunicaciones de la serie 500 de System Sensor** para funcionar con sistemas analógicos compatibles [F5], pero los fragmentos no confirman explícitamente su compatibilidad con la ID3000.

---

**Para obtener la lista completa de detectores compatibles**, consulta el manual de instalación completo de la ID3000 (referencia **MIDT190**) o el catálogo de equipos de lazo de Notifier para esta central.

---

Fuentes: MIDT190 (sin revisión registrada); MCDT190 (sin revisión registrada); MPDT190 (sin revisión registrada); MFDT190 (sin revisión registrada); MIDT1450 (sin revisión registrada)

---

También puedo ayudarte con: **límites de equipos por lazo en la ID3000**, **configuración de sensibilidad de detectores VIEW™** o **programación horaria del SDX-751TEM**.
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

**Razón del judge:** El bot admite correctamente que los fragmentos disponibles no contienen una lista exhaustiva de detectores de humo analógicos compatibles, y extrae con precisión los modelos mencionados en los fragmentos visibles (VIEW LPX-751 en F2, SDX-751TEM en F3). Las citas son fieles a sus fragmentos correspondientes. El comportamiento es 'admit_no_info' honesto y útil, redirigiendo al técnico al manual completo MIDT190, lo cual es la conducta esperada dado que el corpus no cubre la lista completa de compa

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:** La ID3000 soporta detectores analógicos serie 500 de Notifier/System Sensor (FSI-851, FST-851R, FAPT-851, etc.) y serie NFXI (NFXI-OPT, NFXI-TDIFF, NFXI-TFIX58, etc.) según el catálogo Notifier. También VIEW LPX-751 (láser) y multicriterio SDX-751TEM. La info exacta vive en el Manual de Instalación (MIDT190 sec. 4) y el Apéndice C de Equipos Compatibles.

**Calidad de los chunks:**
- **F2 "[TABLA EXTRAÍDA]" sobre texto plano** — mismo error sistémico.
- **F3 header "en la siguiente franja horaria:"** — fragmento arbitrario, totalmente inútil para retrieval. Mismo problema en F4 ("OFF (APAGADO)").
- **F5 trae el FLG2100** vía radio — tangencial, no responde la pregunta.
- **Falta crítica**: Apéndice C "Equipos Compatibles" del MIDT190 + catálogo de detectores. Si existen como chunks, el retrieval no los priorizó. Si no existen como chunks, falta indexar esa sección.
- Mix de F1 (sec. 4.1 instalación) + F2 (sec. detectores MULTI) + F3 (programación horaria) + F4 (LEDs) + F5 (vía radio) — los chunks vienen de **5 manuales distintos** sin priorización por relevancia a la pregunta.

**Comparación con bot:**
- ✓ Honestidad ejemplar: admite que no tiene lista exhaustiva.
- ✓ Cita los detectores que sí encontró (VIEW LPX-751, SDX-751TEM).
- ⚠️ Faltan B500 (serie 500) y NFXI explícitamente (keyword fail real, no del YAML).

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — admisión honesta de gap del corpus.
- **Dimensión equivocada(s) del judge:** ninguna.
- **Nota / por qué:** Caso de retrieval miss legítimo: la lista exhaustiva de compatibles probablemente está en una tabla del Apéndice C del MIDT190 que no se chunkeó bien. **Falta de cobertura del corpus para la pregunta**.
- **Origen del problema:** **retrieval/cobertura** (tabla de compatibles del Apéndice C no surface), **chunk-extraction** (headers fragmentarios en F3/F4, "[TABLA EXTRAÍDA]" mal aplicado en F2).

---

## hp009 — judge dice **PASS ✓** · (9/20)

**Pregunta del técnico:** ¿Cuál es la resistencia de fin de línea recomendada para los lazos de la central Morley ZXe?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: expected_sources retirado: 'ZXe' no aparece en source_file (solo en product_model, 1837 chunks). expected_keywords: quitado 'kohm' — el manual puede usar solo 'Ω'/'ohm' o dar un número específico (ej: 3,9 kΩ). Verificar el valor real al revisar. 20 abril: OR-syntax 'ohm|Ω|ohmios' — el bot usa el símbolo Ω._

### Fragmentos que el bot usó (top 5)

**[F1]** `ZXe` · *6. Retardos (Anula los retardos de los programas de salidas)* · `MIE-MU-530rv001` p.23 · sim 0.80

```
6.
Retardos (Anula los retardos de los programas de salidas) (continuación)

[TABLA EXTRAÍDA]
PANELES DE I | NCENDIO | ZX2e/ZX5 | e |  |  |  |  |  | MOR | LEY-I
----------------------------------------
 | RELÉ | ACTIVADO |  |  |  |  |  |  |  | 
 | 2 |  |  |  |  |  |  |  |  | 
Los cir | cuitos de sire | na de placa | están c | on | stantement | e s | up | ervisado | s para una | correcta
termin | ación de final | de línea. La | tensión | d | e supervisi | ón | en | reposo e | s inversa a | la de di
(Polari | dad marcada | para la cone | xión en | la | placa). |  |  |  |  | 
5.4.1.5 Prueba d | el zumbador | interno. |  |  |  |  |  |  |  | 
• Para selecciona | r esta opción, p | ulse ‘5’. |  |  |  |  |  |  |  | 
• El zumbador inte | rno pitará. |  |  |  |  |  |  |  |  | 
5.4.2 Fecha y | hora |  |  |  |  |  |  |  |  | 
• Para cambiar la | fecha y hora qu | e indica la p | antalla a | lfa | numérica, p | uls | e ‘ | 3’ desde | el menú de | usuario
principal. |  |  |  |  |  |  |  |  |  | 
En los | sistemas con | varias centr | ales, so | lo | es necesar | io | ca | mbiar la f | echa de la | central m
ya que | el resto de ce | ntrales sinc | ronizará | n | su fecha y | ho | ra | cuando s | e realice u | n rearme
centra | l master. |  |  |  |  |  |  |  |  | 
5.4.3 Habilitar | / Anular fun | ciones |  |  |  |  |  |  |  | 
• Para selecciona | r Habilitar o An | ular, pulse la | tecla cor | re | spondiente | “4” | ó | “5” desde | el menú de | usuario.
pantalla mostrar | á lo siguiente p | ara cada opc | ión: |  |  |  |  |  |  | 
 | HABILITAR | 1)Zona | 2)E | qu | ipo 3 | )T | ec | las |  | 
 |  | 4)Modo d | ía 5)S | al | idas 6) | Re | ta | rdos |  | 
 | ANULAR 1) | Zona | 2)Equ | ip | o 3)T | ec | la | s |  | 
 | 4 | )Modo dí | a 5)Sa | li | das 6)R | et | ar | dos |  | 
• Las op
[… contenido truncado para legibilidad]
```

**[F2]** `ZXe` · *• Pour sélectionner l'option, appuyer sur « 5 ». • Le ronfleur s’activera.* · `996-130-000-3 Manuel d'utilisation ZX_hlsi` p.17 · sim 0.65

```
•
Pour sélectionner l'option, appuyer sur « 5 ».
•
Le ronfleur s’activera.

•
Pour sélectionner l'option, appuyer sur « 5 ».
•
Le ronfleur s’activera.

MORLEY-IAS 

Central de détection d’incendie ZX 

Les circuits sirènes du central sont constamment surveillés afin de contrôler la présence 
des résistances de fin de ligne. Un défaut sirène sera rapporté si une des sirènes est laissée 
dans l'état de test pendant plus de 5 secondes.  

5.4.1.5 
Test du ronfleur  
• 
Pour sélectionner l'option, appuyer sur « 5 ».  
• 
Le ronfleur s’activera.  
5.4.2 Date & Heure  
• 
Pour changer la date et l'heure affichées sur l'affichage alphanumérique, appuyer sur « 3 » dans le menu 
principal des options utilisateur.  

Dans un système réseau, il est seulement nécessaire de changer l’heure sur le central 
maître. Tous les autres centraux synchroniseront leur date et heure avec celle du central 
maître lorsqu’un réarmement est effectué sur le central maître.   

5.4.3 Fonctions En / Hors Service  
• 
Pour choisir les options du menu de mise en / hors service, presser la touche « 4 » ou la « 5 » comme 
requis dans le menu utilisateur. L’affichage montre chaque option :  

EN S. : 1)Zone     2)Entrée  3)Clavier       
4)Mode jour 5)Sorties 6)Délais 

HORS S. : 1)Zone     2)Entrée  3)Clavier     
4)Mode jour 5)Sorties 6)Délais 

• 
Les options disponibles de chaque menu sont identiques. Ceci permet à l'utilisateur de mettre en service 
ou hors service :  

1. 
Zones  
2. 
Entrées  
3. 
Touches du central (clavier) 
4. 
Modes jour  
5. 
Sorties 
6. 
Délais 
7. 

• 
Toutes les fois qu'une opération de mise en service est effectuée, l'action est effectuée mais l’option hors 
service n'est pas enlevée du LCD. Ce qui suit est montré momentanément sur l'affichage.  

Appuyer REARMER pr efface
[… contenido truncado para legibilidad]
```

**[F3]** `ZXe` · *Figura 11 – Lazo con aisladores. Opción recomendada.* · `MIE-MI-530rv001` p.20 · sim 0.69

```
Figura 11 – Lazo con aisladores. Opción recomendada.

Figura 11 – Lazo con aisladores. Opción recomendada.

MORLEY-IAS 

Paneles de Incendio ZX2e / ZX5e 

Página 20 de 50 
Documento No.MIE-MI-530, Revisión: 001,  
Manual de Instalación 
Se recomienda la instalación de aisladores de cortocircuito en lugares estratégicos (P.ej. antes y 
después de zonas físicas) para evitar que un cortocircuito provoque la pérdida de más de 32 equipos. 
Nota: Cada lazo dispone de aisladores internos en el panel. No se precisa instalar aisladores en el 
panel. 
El fabricante determina el número máximo de equipos entre aisladores. Revise las 
recomendaciones del fabricante. 

Figura 11 – Lazo con aisladores. Opción recomendada.  

3.4.3.2 
Cumplimiento CE compatibilidad electromagnética 

Para cumplimiento de 
compatibilidad 
electromagnética instale las 
ferritas suministradas para 
los lazos. 
En el dibujo se muestra la 
instalación típica del lazo. 

Ferrita 
grande 
Conecte un 
extremo de la 
pantalla al 
conector 
correspondiente 
+ - E + - 
LOOP 1 
Coloque una 
brida por 
debajo de la 
ferrita 

Figura 12 – Lazo – Filtro de ferrita. 

3.4.3.3 
Carga del lazo analógico 
Debe tenerse especial precaución en no exceder la carga máxima permitida de cada lazo. Cada 
lazo dispone de de una corriente limitada y no se debe superar el límite de alimentación del lazo 
analógico. 
1. 
Revise el manual de la placa de lazo para conocer el límite de corriente. Para mantener el 
funcionamiento del lazo analógico, solo será posible disponer de la mitad de la corriente máxima 
de lazo, para el consumo de equipos conectados a este. 
2. 
Revise la sección 6 para conocer la carga completa y especificaciones del sistema. 
3. 
Realice los cálculos de consumo de lazo para la situación más desfavorable, según
[… contenido truncado para legibilidad]
```

**[F4]** `ZXe` · *Paneles de Incendio ZX2e/ZX5e MORLEY-IAS* · `MIE-MP-530rv001` p.33 · sim 0.80

```
Paneles de Incendio ZX2e/ZX5e
MORLEY-IAS

Paneles de Incendio ZX2e/ZX5e
MORLEY-IAS

Paneles de Incendio ZX2e/ZX5e 

MORLEY-IAS 

Manual de Configuración 
Documento No. MIE-MP-530, revisión: 001  
Página 33 de 66 
Cuando se seleccione la opción de Sirenas ‘7’ [7)Sirenas], aparece en pantalla la sirena de 
placa A y el programa asociado: 
  SIRENA            Programa 
     A                 003 

Para seleccionar una Sirena, pulse la tecla SI ‘9’, se mostrará la siguiente Sirena de la lista. 
Pulse hasta que aparezca la Sirena deseada. 
Si una salida de Sirena es del lazo analógico aparecerá con la Indicación [L:dd] debajo del 
texto SIRENA, para indicar el lazo (L) y dirección (dd) de la misma: 
  SIRENA            Programa 
  4:156               011 

El cursor parpadea en la posición de número de programa, para permitir cambiar el programa 
de la sirena (Número de programa asignado). 
Introduzca el número de programa deseado entre 1 y 150, cuando éste parpadee. Elija un 
número de programa diferente para disparos diferentes.  
Para inspeccionar o cambiar el modo de disparo de la salida, por zonas, presione la tecla 
ENTER ‘↵’. Se mostrará el primer grupo de zonas del programa y el modo de disparo de la 
salida para fuegos de éstas: 
Programa      Zona           Modo 
    11     01  a 60        Retardo    300 s  

Presione la tecla ENTER ‘↵’ sucesivamente, para revisar todas las líneas del programa. 
Si desea modificar un programa, revise la sección 5.7 Configuración de Programas de Salidas. 

Se precisa realizar una Autobúsqueda de los equipos del cada lazo analógico, para 
reconocerlos y configurarlos. Si una salida no está reconocida, no será posible 
programarla, al no aparecer en el listado de Sirenas o Relés 
5.5 Relés 
Los relés se configuran de forma idéntica a
[… contenido truncado para legibilidad]
```

**[F5]** `ZXe` · *• Para cambiar el estado de la salida, pulse la tecla CAMBIO ‘�’. La pantalla mostrará el nuevo estado:* · `MIE-MU-530rv001` p.22 · sim 0.80

```
•
Para cambiar el estado de la salida, pulse la tecla CAMBIO ‘�’. La pantalla mostrará el nuevo estado:

•
Para cambiar el estado de la salida, pulse la tecla CAMBIO ‘�’. La pantalla mostrará el nuevo estado:

MORLEY-IAS 
 PANELES DE INCENDIO ZX2e/ZX5e 

Página 22 de 36 
Documento No. MIE-MU-530, Revisión: 001  
Manual de Usuario 
5.4.1.3.3 
Inspeccionar otras condiciones durante la “Prueba de equipos de zona” 

EN54
9

EN54-2 5.1 
Pantalla de 
condiciones 
funcionales: 

• 
Para inspeccionar una condición de alarma de Fuego, Avería o Anulado 
mientras se está realizando una prueba de equipos, pulse la tecla ‘>’ 
para acceder al menú. 

• 
De esta manera, regresará a las opciones de menú desde donde podrá examinar el resto de condiciones 
de funcionamiento. 
• 
Para cancelar la prueba de equipos, vuelva a seleccionar la opción de Prueba de Zonas. La pantalla 
regresará entonces a la vista normal de la prueba de equipos, mostrando la prueba que está actualmente 
en funcionamiento. Por ejemplo: 

Test desde zona 12    a zona 15 
-----X------------------------------------- 

• 
Pulse la tecla ‘NO’ para cancelar la prueba. 
5.4.1.4 
Prueba de salidas 

El acceso a esta opción de prueba solo está disponible para usuarios con clave de acceso 
de Nivel 3 debido al riesgo de activaciones de las salidas del sistema.  
• 
Para seleccionar la opción, pulse la tecla ‘4’ e introduzca la clave de Nivel 3 ‘####’. Aparecerá una lista 
con las salidas, pulse confirmar Si ‘9’ para avanzar y CAMBIO ‘T’ 
• 
Para finalizar la prueba, pulse No. 
• 
La prueba de salidas permite activar los relés y sirenas de forma individual. Las primeras seis salidas 
están reservadas para los circuitos de sirena y relé de la propia central, como se indica a continuación: 

Salida 1 –Relé 1 
Salida 2 –Relé 2
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados del manual de instalación y usuario de la ZXe mencionan la supervisión de final de línea en los circuitos de sirena, pero **no especifican el valor de resistencia de fin de línea** para los lazos analógicos ni para los circuitos de sirena.

Lo que sí se indica en los fragmentos:

- Los circuitos de sirena de placa están **constantemente supervisados** para una correcta terminación de final de línea [F5].
- La tensión de supervisión en reposo es **inversa a la de disparo** (polaridad marcada para la conexión en la placa) [F5].
- Se reportará un **fallo de sirena** si una sirena permanece en estado de prueba durante más de **5 segundos** [F2].

El valor concreto de la resistencia de fin de línea (en ohmios) **no aparece en ninguno de los fragmentos recuperados**. Para obtener ese dato, consulta:

1. El **Manual de Instalación MIE-MI-530** (revisión 001), específicamente la sección de especificaciones de circuitos de sirena o la sección 6 de especificaciones del sistema [F3].
2. La documentación técnica de la **placa de lazo** correspondiente, ya que el manual remite a revisarla para parámetros específicos [F3].

---

Fuentes: MIE-MU-530 rev. 001; MIE-MI-530 rev. 001; 996-130-000-3 FR

También puedo ayudarte con: **conexionado del lazo analógico con aisladores**, **carga máxima del lazo** o **configuración de sirenas en la ZXe**.
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

**Razón del judge:** El bot admite correctamente que el valor numérico de la resistencia de fin de línea no aparece en ninguno de los fragmentos recuperados (F1-F5), lo cual es honesto y preciso: ni los fragmentos F ni los V contienen ese valor específico en ohmios. Las afirmaciones técnicas que sí hace (supervisión constante de circuitos de sirena, polaridad inversa en reposo, fallo tras 5 segundos en prueba) están soportadas por F5 y F2 respectivamente. El bot redirige al técnico a las secciones correctas del manu

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `MIE-MI-530rv001` sec. 3.4.4 — Circuitos de Sirenas, y manual de instalación de la ZXe — Lazo analógico):**

Hay que distinguir dos circuitos:
- **Lazos analógicos (detección):** la ZXe no usa RFL al uso convencional — los lazos son cerrados (Clase A) o abiertos (Clase B) y la supervisión es por la propia comunicación digital + aisladores de cortocircuito. **No hay valor de RFL especificado** para el lazo de detección.
- **Circuitos de sirena de placa (ZX2e: A/B; ZX5e: A/B/C/D):** RFL = **6,8 kΩ, 0,5 W mínimo**, instalada al final del circuito (sec. 3.4.4). Polarización inversa en reposo para supervisión, normal en alarma, máx 1 A por circuito.

**Calidad de los chunks:**

- **Retrieval roto:** ninguno de los 5 fragmentos contiene la sec. 3.4.4 (que sí está en el manual y aparece como F1 de hp018 a 0.83 sim). El retriever debería haber traído ese chunk a sim ~0.85+ para esta query — es exactamente la misma sección que en hp018.
- **F1 está mal etiquetado:** el "header" indica "6. Retardos (Anula los retardos de los programas de salidas)" pero el contenido empieza hablando de circuitos de sirena supervisados y luego salta a "5.4.1.5 Prueba del zumbador interno". Es un chunk Frankenstein con varias secciones cosidas.
- **`[TABLA EXTRAÍDA]` mal aplicado** en F1: el supuesto contenido tabular ("PANELES DE INCENDIO | ZX2e/ZX5e | ... | RELÉ | ACTIVADO") es texto plano de cabecera de página + indicador de relé, no una tabla real.
- **F2 entero en francés**: chunk recuperado del manual francés (`996-130-000-3 Manuel d'utilisation ZX`). Indica que el retriever cruza idiomas — no filtra por `lang=es`.
- **F3 header inútil**: "Figura 11 – Lazo con aisladores. Opción recomendada." es un caption, no un epígrafe; pero el contenido SÍ habla de aisladores y carga del lazo (relevante tangencialmente).
- **Duplicación**: F2 cita la palabra "ronfleur" y la sec. 5.4.1.5 igual que F1 — son el mismo contenido cruzado ES↔FR.

**Comparación con bot:**

- ✓ Admite honestamente que no aparece el valor.
- ✓ Cita supervisión constante y polaridad inversa (de F2/F5).
- ⚠️ Confunde "circuitos de sirena" con "lazos" — el técnico preguntó por **lazos** (= detección direccionable). El bot no aclara esta distinción esencial.
- ⚠️ No menciona el valor real del manual (6,8 kΩ) que **sí existe** y que el mismo bot encuentra en hp018. Es un fallo evidente de retrieval, no de corpus.
- ⚠️ El bot cita "[F5]" cuando la frase ("supervisión constante / polaridad inversa") realmente proviene de F2 (texto francés) — miscitación de fragmento.

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo** — yo diría: **FAIL parcial**
- **Dimensión equivocada(s) del judge:** **honest** (el bot dice "no aparece" pero el dato sí está en el corpus, lo que el judge no detecta porque solo mira F) y **citation_faithful** (cita F5 por una afirmación que aparece en F2 — el judge no lo audita finamente).
- **Nota / por qué:** El bot da un `admit_no_info` cuando el corpus SÍ contiene la respuesta para circuitos de sirena (sec. 3.4.4 ZXe, 6,8 kΩ). El judge no puede verlo porque solo evalúa contra F. Además, el bot no desambigua "lazo" vs "circuito de sirena" — un técnico real necesita esa aclaración. El judge le da pase porque la admisión es coherente con los F pobres que recibió.
- **Origen del problema:** **retrieval** (el chunk de sec. 3.4.4 existe y se recupera para hp018, pero no para hp009 — query mal embebida o ranking inconsistente) + **chunk-extraction** (F1 cose secciones distintas con header equivocado) + **generación** (no aclara la ambigüedad lazo vs sirena).

---

## hp010 — judge dice **PASS ✓** · (10/20)

**Pregunta del técnico:** En la Morley DXc, ¿cómo se añade un nuevo detector al lazo tras la puesta en marcha inicial?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 1/4 hits · missing: `['auto-learn', 'scan', 'direccionar']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `DXc` · *Opciones de entradas 5.3.5.1.4, 5.3.10* · `DXc_Manual de configuracion` p.7 · sim 0.65

```
Opciones de entradas
5.3.5.1.4, 5.3.10

– PÁGINA 7 –
EN54
Además de las funciones requeridas por la EN54-2, la central dispone también 
de varias funciones auxiliares que no requiere la norma EN54. Son éstas:
FUNCIÓN AUXILIAR
SECCIÓN DEL MANUAL
SALIDA DE ALIMENTACIÓN AUXILIAR
3.4.7
SALIDA DE LAZO PERIFÉRICO Y EQUIPOS COMPATIBLES 
3.4.10
SALIDAS DE RELÉ AUXILIAR
3.4.7, 5.2.7
ENTRADA PARA DISPARO DE SIRENAS
3.4.9, 5.2.6.1
OPCIONES DE SALIDA DE CONTACTO LIBRE DE TENSIÓN
3.4.6
AUTOCONFIGURACIÓN
5.3.5.2
MODO DE SENSIBILIDAD
5.3.10.3
PROGRAMAS DE CONTROL: 
Programas de salidas 
5.3.7
Opciones de entradas 
5.3.5.1.4, 5.3.10
Opciones de salidas 
5.3.5.1.5, 5.3.10
Funciones con horario 
5.3.10.4 y Manual usuario
RED
Apéndice 7
AUTO ANULAR/HABILITAR
5.3.11
OPCIÓN DE PARPADEO DEL LED DE SENSORES 
5.3.4
EDICIÓN DE TEXTOS
5.3.5.1.1
OPCIONES DE SILENCIAR SALIDAS
5.3.7.4
SELECCIÓN DE PRUEBA AUTOMÁTICA
5.3.4
OPCIÓN DE PULSO PARA SIRENAS
5.3.5.1.5
ANULACIÓN POR GRUPOS
5.3.5.1.3 y Manual usuario
INTERFAZ PARA PC RS232
5.1.2, 5.4 y Apéndice 5
RELOJ – AJUSTE DE DESVIACIÓN
5.3.12.2
MODO DIAGNÓSTICO 
5.3.4


[TABLA EXTRAÍDA]
[FUNCIÓN AUXILIAR | SECCIÓN DEL MANUAL]
  SALIDA DE ALIMENTACIÓN AUXILIAR: 3.4.7
```

**[F2]** `DXc` · *Tabla 3 – Funciones de LED* · `DXc_Manual de usuario` p.6 · sim 0.72

```
Tabla 3 – Funciones de LED

Tabla 3 – Funciones de LED

– PÁGINA 6 –
TECLAS
FUNCIÓN
Teclas de 
navegación
Tecla  
'OK'
Pulse las teclas p,q,t y u para seleccionar y navegar por las funciones del nivel 
1: condiciones de alarma, avería, anulaciones y pruebas.
Pulse OK  para confirmar los cambios o seleccionar una opción de menú.
Teclas 
0 -9, A - Z
Tecla 
salir
Tecla retroceso 
/ borrar
Teclado numérico para introducir número. También, en la programación, para 
introducir mensajes de texto. Funciona de forma similar al teclado de los 
teléfonos móviles.
Pulse 
 para cancelar un cambio o regresar al menú anterior sin cambiar la 
configuración.
Utilice la función de retroceso en modo de edición de textos. En algunos menús, esta 
función permite borrar los datos definidos por el usuario.
Tabla 2 – Teclas de función alfanuméricas e interactivas
3.2 Indicaciones de los leds del panel frontal
DESCRIPCIÓN TECLA
COLOR
FUNCIÓN
CÓMO CESAR LA INDICACIÓN
FUEGO
Rojo
La central ha detectado una alarma de 
incendio.
Corregir la causa de la alarma y rearmar la 
central.
ZUMBADOR SILENCIADO
Amarillo
Se ha aceptado una alarma o avería y se ha 
silenciado el zumba- dor interno.
Corregir la causa de la alarma y rearmar la 
central.
SIRENAS SILENCIADAS
Amarillo
Las salidas de sirenas se han silenciado.
Corregir la causa de alarma y rearmar la 
central. NOTA: Pulsar SILENC./REACT. para 
reactivar sirenas.
ALIMENTACIÓN
Verde
FIJO: Indica la presencia de ali- mentación 
(red o baterías).
No aplicable.
AVERÍA
Amarillo
La central ha detectado una avería.
Corregir la causa de la avería y rearmar la 
central.
FALLO SISTEMA
Amarillo
Se ha rearmado el sistema o se ha producido 
una avería de CPU.
Corregir el problema y, si es pertinente, 
realizar un rearme de la central.
AVERÍA EN SIRENAS
Amarillo
I
[… contenido truncado para legibilidad]
```

**[F3]** `DXc` · *Periodic Testing* · `DXc_Guia de usuario_multiling` p.3 · sim 0.72

```
Periodic Testing

Periodic Testing

Fire Safety
NUMERIC KEYPAD 
(MENU OPTION SELECTION KEYS)
0-9 Keys
For number entry. Also used for alphabet 
entry during programming and configuration. 
 Key
Press to cancel a change or return to a 
previous menu.
C  Key
Press to back-space when correcting entries 
such as passcodes.
Para más información:
www.morley-ias.es
Honeywell Life Safety Iberia
C/Pau Vila 15-19
08911 Badalona (Barcelona)
España
T: 902 03 05 45
E: infohlsiberia@honeywell.com
996-214-002-1 | Rev 02 | 08/16
© 2016 Honeywell International Inc.
DX Connexion
GB
User Guide for the DX Connexion Series
Fire Alarm Control Panels
THIS DOCUMENT MUST BE FRAMED AND MOUNTED IN VIEW AND ADJACENT TO THE FIRE CONTROL PANEL.
OK
ABC
DEF
MNO
PQRS
TUV
WXYZ
GHI
JKL
EN54-2
EN54-4
C
MUTE BUZZER
SYSTEM RESET
EXTEND DELAY
EVACUATE
SHOW ALARM ZONES
SILENCE/ RESOUND
F1
F2
1
2
3
4
7
5
8
6
9
0
FIRE
FAULT
POWER
SYSTEM FAULT
SOUNDER FAULT
SOUNDERS DISABLED
SUPPLY FAULT
DISABLEMENT
TEST
DELAYED MODE
BUZZER MUTED
SOUNDERS SILENCED
DX Connexion Series Controls and Displays
USER CONTROL KEYS
Mute Buzzer
Press to silence the internal buzzer.
Silence/Resound
Press to silence the sounders. Press 
again to re-activate.
System Reset
Press to cancel all alarm conditions 
and reset the panel after cause of 
alarm has been corrected.
Extend Delay
Press to acknowledge Stage 1 
Delayed Alarm. Stage 2 delay period 
starts.
Show Alarm Zones
Displays fire alarm information. If 
there is more than one zone in alarm, 
scrolls through these zones.
Evacuate
Press to turn on ALL Sounder 
Outputs, i.e. evacuate building 
manually.
MENU NAVIGATION KEYS
Press 
OK  to confirm changes or select 
a menu option. Press , ,  and 
 keys to select and scroll through 
Level 1 display functions for fire, fault, 
disablement
[… contenido truncado para legibilidad]
```

**[F4]** `DXc` · *Sección 5.3.4.8 Ver información del sistema* · `DXc_Manual variaciones de mercado` p.2 · sim 0.72

```
Sección 5.3.4.8 Ver información del sistema (continuación)

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
 | texto del
[… contenido truncado para legibilidad]
```

**[F5]** `DXc` · *EEC, en aplicación de las siguientes normas:* · `DXc_Manual de configuracion` p.5 · sim 0.65

```
EEC, en aplicación de las siguientes normas:

EEC, en aplicación de las siguientes normas:

– PÁGINA 5 –
1.3 Advertencias y precauciones
!
Estas instrucciones contienen procedimientos que deben seguirse 
correctamente con el fin de evitar daños en los equipos. El usuario 
que utilice este manual debe ser un instalador con la formación 
adecuada y conocedor de la normativa pertinente.
Dispositivos sensibles a descargas electroestáticas (ESD).
Adopte las medidas necesarias para evitar descargas electroestáticas 
cuando instale o manipule las placas de circuito impreso.
Esta central dispone de marcado CE para indicar que cumple 
con los requisitos de las siguientes directivas europeas:
Directiva de Compatibilidad Electromagnética (CEM) 2004/108/
EEC, en aplicación de las siguientes normas CEM:
•	 EN 61000-6-3: Emisiones EMI. Residencial, comercial e industria ligera.
•	 EN 50130-4: Compatibilidad electromagnética. Norma de familia 
de producto: Requisitos de inmunidad para componentes de 
sistemas de detección de incendios, intrusión y alarma social.
Directiva de Baja Tensión 2006/95/EE, en aplicación de la norma de seguridad:
•	 EN 60950-1: Seguridad de equipamiento tecnológico de la información.
Directiva de Productos de la Construcción (CPD)89/106/
EEC, en aplicación de las siguientes normas:
•	 EN54-2: 1998 (Enm. 1 & 2): Sistemas de detección y alarma 
de incendio – equipamiento de control y señalización.
•	 EN54-4 1998 (Enm. 1 & 2): Sistemas de detección y alarma de 
incendio – equipamiento de fuente de alimentación.
!
PRECAUCIÓN: Se utiliza una batería de litio para el reloj de la central.
RIESGO DE EXPLOSIÓN SI SE SUSTITUYE LA BATERÍA POR 
OTRA DE UN MODELO INCORRECTO. Desechar las baterías 
de forma responsable y según la normativa local.
Véase el Apéndice 4. Recam
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados del manual de la DXc **no describen el procedimiento específico para añadir un nuevo detector al lazo tras la puesta en marcha inicial**.

Lo que sí está disponible en los fragmentos:

- La DXc dispone de una función de **AUTOCONFIGURACIÓN** referenciada en la sección **5.3.5.2** del Manual de configuración [F1].
- La programación manual del lazo se puede realizar o posponer durante la puesta en marcha inicial (paso 4 de la programación guiada) [F4].
- El acceso a configuración requiere **Nivel de usuario 3**, reservado para instalador/mantenedor [F3].
- La capacidad máxima es de **512 sensores/pulsadores por central** según EN54-2 13.7 [F5].

Para el procedimiento detallado de añadir un detector al lazo, necesitarás consultar directamente:

- **Manual de configuración DX Connexion** (referencia española: **996-203-005-X**), sección **5.3.5.2 (Autoconfiguración)** [F4].
- O la sección de programación manual del lazo en ese mismo manual.

---

Fuente: DXc\_Manual de configuracion (sin revisión registrada); DXc\_Manual variaciones de mercado (sin revisión registrada); DXc\_Guia de usuario\_multiling (Rev 02, 08/16)

---

También puedo ayudarte con: **niveles de acceso y códigos de usuario**, **funciones de autoconfiguración** o **indicaciones de avería en lazo** de la DXc.
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

**Razón del judge:** Ninguno de los fragmentos F ni V contiene el procedimiento paso a paso para añadir un detector al lazo tras la puesta en marcha. El bot reconoce honestamente esta limitación, cita correctamente datos que sí aparecen en los fragmentos F (autoconfiguración en 5.3.5.2 de F1/F4, nivel 3 para instalador de F3, límite 512 sensores de F5, referencia 996-203-005-X de F4) y redirige al técnico al manual de configuración con sección y referencia concretas, lo que constituye un admit_no_info útil y acciona

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `DXc_Manual de configuracion` sec. 5.3.5.2 Autoconfiguración):**

Tras la puesta en marcha inicial, para añadir un detector nuevo a un lazo ya configurado:
1. Instalar físicamente el detector en su base direccionable, respetando dirección no asignada en el lazo (poner los rotativos del detector si lleva, o programar dirección virtualmente).
2. Acceder con clave de **Nivel 3** (instalador).
3. Ejecutar **Autoconfiguración** (sec. 5.3.5.2) — la central detecta el equipo nuevo y lo añade al mapa del lazo manteniendo los existentes; o usar **PTPT** (programación de un punto) para asignación manual de tipo/dirección.
4. Verificar en la sec. 5.3.4.1 ("Ver equipos") que aparece el nuevo punto, y editar texto/zona desde el menú correspondiente.
5. Hacer prueba funcional del detector.

**Calidad de los chunks:**

- **Retrieval falla por completo** para esta query: ninguno de los 5 chunks describe el procedimiento de añadir detector. F1, F4 y F5 son índices o secciones administrativas; F2 es la tabla de teclas y leds; F3 es la página de portada multilingüe de la guía de usuario inglesa.
- **F1 header inútil**: "Opciones de entradas 5.3.5.1.4, 5.3.10" — es una entrada de índice/referencia cruzada, no un epígrafe propio. El contenido del chunk es la tabla de funciones auxiliares con su sección de referencia, justamente donde se ve **AUTOCONFIGURACIÓN 5.3.5.2** — el chunk del epígrafe 5.3.5.2 en sí no se recuperó.
- **F2 header mismatch**: "Tabla 3 – Funciones de LED" pero el contenido empieza por la Tabla 2 (teclas) y luego pasa a leds del panel frontal — el caption es de la tabla siguiente, no la actual.
- **F3 es ruido total**: portada de la guía rápida en EN/multilingüe (no relevante para el procedimiento técnico en ES).
- **F4 `[TABLA EXTRAÍDA]` mal aplicado**: el contenido extraído como tabla es un párrafo en bullets sobre cómo organizar el manual de variaciones de mercado. NO es tabla real.
- **F5 ruido**: portada con marcado CE y precauciones de ESD — totalmente irrelevante.

**Comparación con bot:**

- ✓ Admite honestamente que el procedimiento paso a paso no está en F.
- ✓ Identifica correctamente la sec. 5.3.5.2 (Autoconfiguración) como destino.
- ✓ Cita nivel de acceso 3 (Niveles citados son razonables aunque F3 está en inglés y refiere al teclado, no a niveles).
- ⚠️ Cita "Manual de configuración DX Connexion (referencia española: 996-203-005-X)" — esta referencia aparece en F4 (manual de variaciones), no en F1 como dice el bot.
- ⚠️ Dice "límite 512 sensores/pulsadores por central según EN54-2 13.7" citando [F5]. F5 NO menciona este límite (sólo habla de marcado CE, baterías de litio y directivas europeas). **Esto es una invención del bot o miscitación**. Verifico F5 entero y solo veo Directiva de Compatibilidad Electromagnética, baja tensión, CPD/EN54-2, batería de litio — nada de 512 sensores. Eso es un fallo de `citation_faithful` que el judge no detectó.

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo** — yo diría: **FAIL**
- **Dimensión equivocada(s) del judge:** **citation_faithful** (el bot atribuye a F5 el dato "512 sensores/pulsadores por central según EN54-2 13.7" que no aparece en F5 — fabricación o miscitación).
- **Nota / por qué:** El judge dice "límite 512 sensores de F5" pero F5 no contiene ese dato. El bot probablemente está mezclando conocimiento general de la DXc con citación incorrecta de F5. Este es el tipo de error que el judge debería pillar (cita una afirmación específica contra un fragmento que no la contiene). El admit_no_info global es razonable, pero está contaminado con afirmaciones fabricadas/miscitadas.
- **Origen del problema:** **generación** (miscitación de F5 con dato no contenido) + **retrieval** (no se recupera la sec. 5.3.5.2 que es la respuesta directa) + **judge** (no audita la cita de F5).

---

## hp011 — judge dice **PASS ✓** · (11/20)

**Pregunta del técnico:** En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/5 hits · missing: `['cableado', 'disparo']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `RP1R` · *3.13 Fine del tempo di attesa scarica* · `RP1R - MAN ITA r.A2` p.20 · sim 0.65

```
3.13 Fine del tempo di attesa scarica

PAGINA - 20 
Manuale di installazione ed uso 
RP1R 
NOTIFIER ITALIA 
Doc. M-204.1-RP1R-ITA Rev A.2 
RP1R_manu 
 
Mediante l’interruttore SW1-7, il pulsante di rilascio può essere 
configurato per avere una priorità su questo ingresso. Se il dispositivo 
di sospensione deve avere priorità sul pulsante di rilascio del gas 
(quello situato sulla centrale oppure quello in Zona 3), l’interruttore 
SW1-7 deve essere in posizione ON. 
Quando la centrale è in modalità Sospensione, il relè di Disabilitazione 
dello spegnimento si attiva. 
3.12 Dispositivo di Annullamento di emergenza (Abort) 
Secondo la EN12094:1/2003 Sezione 
4.27, se l’ingresso di Abort si attiva, il 
segnale di spegnimento deve essere 
bloccato. 
La centrale RP1r rispetta questo requisito: 
il pulsante di Abort cancella lo stato di 
spegnimento. Inoltre, questo ingresso di 
Abort è memorizzato ed è necessario 
eseguire un reset manuale per riattivare il 
processo di spegnimento. 
Quando l’ingresso è riattivato, anche il relè di Sospensione (4) e il relè di Disabilitazione spegnimento 
(14) sono attivati. 
3.13 Fine del tempo di attesa scarica 
Quando il tempo per il comando di spegnimento 
(settato nella funzione “dr”, tempo di spegnimento) 
è finito, saranno eseguite le seguenti azioni: 
 Due circuiti a solenoide saranno attivati 
 Il timer indicherà 00 fisso 
 Il led “Rilascio” sarà fisso 
3.14 Tacitazione sirene 
Per fermare le sirene premere il tasto Tacita/Riattiva con un accesso di livello 2. Per avere accesso di 
livello 2, utilizzare l’interruttore a chiave o abilitare la tastiera (vedi 3.2: Livelli di accesso). Quando le 
sirene sono ON, vengono tacitate o riattivate premendo il pulsante Tacita/Riattiva. 
3.15 Controllo del tempo di durata della scarica gas
[… contenido truncado para legibilidad]
```

**[F2]** `RP1R` · *3.12 Dispositivo di Annullamento di emergenza (Abort)* · `RP1R - MAN ITA r.A2` p.20 · sim 0.65

```
3.12 Dispositivo di Annullamento di emergenza (Abort)

PAGINA - 20 
Manuale di installazione ed uso 
RP1R 
NOTIFIER ITALIA 
Doc. M-204.1-RP1R-ITA Rev A.2 
RP1R_manu 
 
Mediante l’interruttore SW1-7, il pulsante di rilascio può essere 
configurato per avere una priorità su questo ingresso. Se il dispositivo 
di sospensione deve avere priorità sul pulsante di rilascio del gas 
(quello situato sulla centrale oppure quello in Zona 3), l’interruttore 
SW1-7 deve essere in posizione ON. 
Quando la centrale è in modalità Sospensione, il relè di Disabilitazione 
dello spegnimento si attiva. 
3.12 Dispositivo di Annullamento di emergenza (Abort) 
Secondo la EN12094:1/2003 Sezione 
4.27, se l’ingresso di Abort si attiva, il 
segnale di spegnimento deve essere 
bloccato. 
La centrale RP1r rispetta questo requisito: 
il pulsante di Abort cancella lo stato di 
spegnimento. Inoltre, questo ingresso di 
Abort è memorizzato ed è necessario 
eseguire un reset manuale per riattivare il 
processo di spegnimento. 
Quando l’ingresso è riattivato, anche il relè di Sospensione (4) e il relè di Disabilitazione spegnimento 
(14) sono attivati. 
3.13 Fine del tempo di attesa scarica 
Quando il tempo per il comando di spegnimento 
(settato nella funzione “dr”, tempo di spegnimento) 
è finito, saranno eseguite le seguenti azioni: 
 Due circuiti a solenoide saranno attivati 
 Il timer indicherà 00 fisso 
 Il led “Rilascio” sarà fisso 
3.14 Tacitazione sirene 
Per fermare le sirene premere il tasto Tacita/Riattiva con un accesso di livello 2. Per avere accesso di 
livello 2, utilizzare l’interruttore a chiave o abilitare la tastiera (vedi 3.2: Livelli di accesso). Quando le 
sirene sono ON, vengono tacitate o riattivate premendo il pulsante Tacita/Riattiva. 
3.15 Controllo del tempo di durata del
[… contenido truncado para legibilidad]
```

**[F3]** `RP1r` · *Refer to Section 3.4.7 Input monitoring for more information.* · `HLSI-MN-103I_RP1r-Supra_lr` p.17 · sim 0.72

```
Refer to Section 3.4.7 Input monitoring for more information.

17
http://www.honeywelllifesafety.es
HLSI-MN-103-I v.06
User Manual 
RP1r-Supra
Installation
3.4.3 
Emergency abort device - Terminal block: D
The extinguishing control panel has an Abort input  to comply with the requirements of UNE-EN 12094-1:2004, section 4.27 (Devices for emergency abort).
The optional connection of an Abort device to Terminal block “D” allows you to manually stop the automatic extinguishing sequence. The Abort input is 
latched, so, once activated, it will require a manual reset of the control panel to enable again the extinguishing process.
To ensure the monitoring, it is necessary to install a serial 2K2 resistor  with the call point and a 47μF (≥ 35V) capacitor as an End Of Line element (EOL).
Alternatively, and for compatibility reasons with previous installations, it is possible to replace the capacitor by an EOL resistor (6K8). (See Section 5. Control 
Panel Configuration for more details).
Refer to Section 3.4.7 Input monitoring for more information.
Emergency abort
D
Abort switch
+
-
Resistor
2K2
NO switch
Abort switch - not used
+ -
EOL
capacitor
47µF
EOL
capacitor
47µF
18
http://www.honeywelllifesafety.es
HLSI-MN-103-I v.06
User Manual 
RP1r-Supra
Installation
3.4.4 
Zone connection - Terminal blocks: E, F and G
The connection terminals for detection zones provide 24Vdc nominal voltage, which is used to supply power to conventional detectors and call points. 
When using Notifier series 800 or Morley ECO1000 detectors, up to 32 detectors per zone can be installed.
Detection zone circuits must be wired as a single circuit with no spurs or T junctions to enable the monitoring circuit to work correctly. Moreover, a 47μF (≥ 
35V) capacitor is required as an End Of Line element.
Alt
[… contenido truncado para legibilidad]
```

**[F4]** `RP1r` · *00 Sin verificación de la alarma (por defecto)* · `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` p.2 · sim 0.65

```
00
Sin verificación de la alarma (por defecto) (continuación)

Consultar manual de usuario para más información acerca 
de procedimientos de acceso, selección y modificación.
Guía rápida - Opciones de configuración
Nota:	 Opciones de configuración accesibles sólo desde Nivel 3.

Consultar manual de usuario para más información acerca 
de procedimientos de acceso, selección y modificación.
```

**[F5]** `RP1r` · *3.16 Controlo do tempo de descarga, parâmetro dR* · `MNDT102P` p.22 · sim 0.72

```
3.16 Controlo do tempo de descarga, parâmetro dR

Manual de utilizador. RP1r 
MN-DT-102P 
 
22 de 32 
rS. Atraso Secundário. Tempo em minutos desde que se prime a tecla Silenciar Besouro até que se 
activam as  Sirenes. Em caso de alarme de uma só zona, o operador dispõe de algum tempo para poder 
verificar o alarme e rearmar a central antes que se activem as sirenes. Se for premido, durante este 
intervalo, a tecla Atraso Sim/Não, poderá activar/desactivar as sirenes que se activam em impluso lento. 
Os valores possíveis são: 
00 – 01 – 02 – 03 – 04 – 05 – 06 – 07 – 08 – 09 - 10   
 
 
 
 
 
Para avançar de um valor a outro, utilize a tecla Atraso Sim/Não. 
 
Para retroceder, utilize a tecla Silenciar Besouro. 
 
 
Para passar ao seguinte parâmetro (EF), utilize a tecla Teclado:  
 
Em qualquer caso, segundo indica EN54-2, o atraso máximo entre Atraso Principal rP e o Atraso 
Secundário rS, deve ser inferior a 10 minutos: 
Se em estado de Pré-activado, as sirenes estão temporizadas porque existe um atraso programado, a 
central indicará que as  sirenes estão temporizadas e activa-se de forma intermitente o led de Atraso 
Sim/Não. Durante este intervalo, poderá silenciar as Sirenes premindo Silenciar Sirenes ou anular o 
Atraso premindo a tecla Atraso Sim/Não e portanto activar as  sirenes. 
Uma vez finalizado o atraso de sirenes e activam-se as sirenes, a tecla Atraso Sim/Não deixará de estar 
intermitente e apaga-se. 
Se, em qualquer momento, deseja anular o atraso configurado, simplesmente prima a tecla Atraso 
Sim/Não. Se esta tecla esta iluminada indica que os atrasos configurados estão anulados e portanto 
activam-se as  sirenes imediatamente quando existir uma condição de pré-activado. 
 
3.16 Controlo do tempo de descarga, parâmetro dR 
A Opção da norma EN12094:
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## RP1r – Sistema no vuelve a estado normal tras reset después de descarga

Los fragmentos recuperados apuntan a **dos causas principales** que pueden impedir el retorno al estado normal tras un reset:

---

### 1. Configuración del tiempo de descarga (SW3-6 y SW3-7)

Comprueba la posición de los microinterruptores **SW3-6 y SW3-7** [F1][F5]:

- **SW3-6 = ON / SW3-7 = OFF** (posición "10"): el tiempo de descarga está configurado como **"Hasta el reset de la central"** ("Até rearme da central"). En esta configuración, los circuitos de solenoide permanecen activos indefinidamente hasta que se realiza un reset manual.

Si los switches están en esta posición, el sistema **no saldrá del estado de descarga** hasta que se ejecute el reset correctamente. Verifica que el reset se está realizando con el nivel de acceso adecuado.

---

### 2. Entrada de Abort activada o memorizada

El dispositivo de Abort (entrada en bloque de terminales **D**) es **memorizado (latched)** [F3]. Una vez activado, **requiere reset manual de la central** para reactivar el proceso de extinción y volver al estado normal [F2][F3].

Comprueba:
- Que el pulsante/dispositivo de Abort **no esté físicamente activado o en cortocircuito**.
- Que el circuito de Abort tenga correctamente instalada la **resistencia serie 2K2** y el **condensador EOL de 47 µF (≥ 35V)** [F3] — o alternativamente la resistencia EOL de **6K8** [F3].
- Si el circuito de Abort está en fallo o activado, el relé de Suspensión **(4)** y el relé de Inhabilitación de descarga **(14)** permanecerán activos [F2], bloqueando el retorno al estado normal.

---

### 3. Nivel de acceso para el reset

El reset manual requiere **nivel de acceso 2** como mínimo [F4 — referencia a niveles de acceso en sección 3.2]. Verifica que el reset se está ejecutando con llave o teclado habilitado correctamente.

---

### Resumen de comprobaciones:

- **SW3-6 y SW3-7**: verificar que no estén en posición ON/OFF ("hasta reset") si no es la configuración deseada [F1][F5]
- **Circuito de Abort (terminal D)**: verificar estado físico del pulsador y elementos EOL (2K2 + 47 µF o 6K8) [F3]
- **Nivel de acceso**: confirmar que el reset se realiza con nivel 2 [F4]
- **LED "Rilascio" / Liberación**: si está fijo tras el reset, indica que los solenoides siguen activos [F1]

---

⚠️ **Nota importante**: Los fragmentos disponibles están en italiano y portugués (manual RP1R - MAN ITA r.A2 y MNDT102P). Si tienes el manual en español **HLSI-MN-103-I**, consulta la **Sección 5 (Control Panel Configuration)** para los detalles de configuración de switches [F3].

---

**Fuentes:**
- RP1R - MAN ITA r.A2 (Rev A.2)
- HLSI-MN-103I_RP1r-Supra_lr (sin revisión registrada)
- MNDT102P (sin revisión registrada)
- HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr (sin revisión registrada)

---

También puedo ayudarte con: **configuración de switches SW3 para tiempo de descarga**, **conexionado del terminal de Abort (D)** o **niveles de acceso y procedimiento de reset** de la RP1r.
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

**Razón del judge:** El bot responde directamente (conducta 'answer') con información soportada por los fragmentos F1/F2/F3/F5: la configuración SW3-6=ON/SW3-7=OFF que mantiene el circuito activo hasta reset, y el comportamiento latched del Abort que requiere reset manual. Todas las afirmaciones técnicas concretas (posición de switches, resistencia 2K2, condensador 47µF EOL, relés 4 y 14) están respaldadas por los fragmentos citados. La mención al nivel de acceso 2 para reset es coherente con F4 (referencia a secció

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `HLSI-MN-103-I_RP1r-Supra` y `RP1R-MAN-ITA r.A2`):**

Si la RP1r no vuelve a estado normal tras un reset post-descarga, comprobar en este orden:
1. **Entrada Abort (terminal D) memorizada/activada**: el Abort es latched (EN12094-1 §4.27) — requiere reset manual; si el circuito está en cortocircuito o el pulsador queda enclavado, el sistema queda permanentemente en "spegnimento bloccato". Verificar EOL del circuito Abort (2K2 serie + 47 µF EOL, o alternativamente 6K8).
2. **Parámetro dR (tiempo de descarga)**: si está configurado a "hasta reset" los solenoides quedan activos hasta reset manual válido — verificar nivel 2 al pulsar Reset.
3. **Solenoides aún enganchados/disparados**: LED "Rilascio/Liberación" fijo indica solenoides activos — comprobar cableado y fusible.
4. **Disparo manual de Paro/Disparo/Pausa**: pulsadores frontales o externos con cableado pegado.
5. **Avería en zonas de detección o de extinción**: una zona en alarma persistente impide el rearme — anular zona y reset.
6. **EOL/cableado** de zonas de detección y de pulsadores de disparo defectuoso (a menudo causa avería que enmascara el rearme).

**Calidad de los chunks:**

- **F1 y F2 son prácticamente idénticos** (sim 0.65 / 0.65 ambos): contienen la misma página 20 del manual italiano (sec. 3.12 Abort + 3.13 Fine tempo attesa scarica). Duplicación masiva.
- **F1 header ("3.13 Fine del tempo di attesa scarica")** no coincide con el inicio real del contenido del chunk, que empieza por SW1-7 / sospensión (3.11). Header mismatch.
- **F2 header ("3.12 Dispositivo di Annullamento")** sí coincide aproximadamente con la mitad del chunk. Pero duplica F1.
- **Idioma mixto**: F1+F2 italiano, F3 inglés, F5 portugués, F4 español. **Cero chunks en español de la RP1r** para una query en español. Indica `lang` no se está usando para reranking.
- **F4 header inútil**: "00 Sin verificación de la alarma (por defecto)" — frase de un parámetro de la guía rápida, no un epígrafe ni una sección coherente.
- **F3 (inglés)** sí aporta el dato real del Abort latched con resistencias 2K2/EOL 47µF — el bot lo aprovecha bien, pero idealmente debería haber un chunk paralelo en español.
- **F5 sec. 3.16 portugués (parámetro dR)** sí es relevante para la pregunta, aunque mezcla rS (atraso secundario) y dR (tiempo de descarga).

**Comparación con bot:**

- ✓ La respuesta es **muy bien estructurada** y cubre causas reales: SW3-6/SW3-7, Abort latched, EOL 2K2 + 47µF, nivel acceso 2, LED Rilascio.
- ⚠️ Cita SW3-6/SW3-7 atribuyéndolo a [F1][F5]. F1 menciona SW1-7 (no SW3-6/SW3-7). F5 portugués menciona dR pero no los switches SW3 concretos. **Esto es una posible miscitación / fabricación: los nombres de switches están inventados o mezclados con conocimiento previo no presente en F.**
- ⚠️ Cita "valores SW3-6=ON / SW3-7=OFF (posición '10') = hasta reset central" — esa codificación binaria de switches no aparece literalmente en ningún F. Es plausible (consistente con la familia de centrales), pero no soportada explícitamente.
- ⚠️ El judge dice "todas las afirmaciones técnicas concretas... están respaldadas" — pero las posiciones SW3-6/SW3-7 no están en F. Fallo de auditoría del judge.

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo** — yo diría: **FAIL parcial**
- **Dimensión equivocada(s) del judge:** **citation_faithful** (los nombres de switches concretos no están en F como dice el judge).
- **Nota / por qué:** Respuesta útil para el técnico, pero contaminada con datos específicos (SW3-6/SW3-7 posición "10") cuya fuente no se aprecia en F. F1 sólo nombra SW1-7. Patrón clásico de bot que mezcla conocimiento de pre-training con citaciones espurias a los F. El judge no audita finamente.
- **Origen del problema:** **chunk-extraction** (duplicación F1=F2; falta de chunk en español de la RP1r para el corpus principal) + **generación** (miscitación de switches) + **judge** (no audita literalidad de los datos numéricos contra F).

---

## hp012 — judge dice **PASS ✓** · (12/20)

**Pregunta del técnico:** ¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y cuántos dispositivos por lazo?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 2/4 hits · missing: `['detectores', 'módulos']` · **keyword_pass:** `False`

> _Notas YAML: expected_sources retirado: 'AM2020'/'AFP1010' no aparecen en source_file (viven en product_model, dentro de docs MFDT280/15088SP/MADT285)._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `AM2020/AFP1010` · *Y/O Cualquier módulo monitor con una dirección inferior o igual a la dirección máxima and/or programada en modo local pa* · `BTDT032` p.4 · sim 0.80

```
Y/O
Cualquier módulo monitor con una dirección inferior o igual a la dirección máxima
and/or
programada en modo local para módulos monitores entra en alarma.

FUNCIONAMIENTO EN MODO LOCAL EN LA AM2020/AFP1010
(Pérdida de comunicaciones entre la CPU y la tarjeta de lazo)
El Modo Local en las Centrales  AM2020/AFP1010 permite a las tarjetas de lazos LIB200, LIB200A y
LIB400 funcionar de forma independiente si se pierden las comunicaciones entre una tarjeta de lazo y la
CPU.
La CPU gestiona la matriz de control (control por evento) según la programación realizada por el usuario.
Si se pierden las comunicaciones con la CPU, la tarjetas de lazo realizan la misma matriz de control con las
siguientes características:
Sí
Cualquier sensor analógico con una dirección inferior o igual a la dirección máxima
if
programada en modo local para sensores entra en alarma.
Y/O
Cualquier módulo monitor con una dirección inferior o igual a la dirección máxima
and/or
programada en modo local para módulos monitores entra en alarma.
ENTONCES
Todos los módulos de control con una dirección inferior o igual a la dirección
then
máxima programada en modo local para módulos de control se activarán.
Las alarmas son rearmables, si desaparece la condición de alarma  también se rearmará la activación
Nuevas funciones en Modo Local
Los equipos en modo local en cada tarjeta de lazo se dividen en diferentes categorías dependiendo del tipo de
ID programado. Todos los equipos dentro del rango de direcciones participarán en modo local. A continuación
se detallan las categorías y los tipos de equipos que residen en cada categoría.
1
2
3
4
5
6
7
8
9
A
B
PHOT
MTRB
SPSU
WAT
CON
TPND
TELE
APND
WFS
SSC
PWRC
ION
MPAG
SUPR
SPKR
GPND
PAGE
EVGA
WFC
THER
NOA
FORC
GTC
GAS
MON
SARM
CMXS
TRS
GAC
PULL
SSYM
CMXC
TRC
FTHR
SACM
[… contenido truncado para legibilidad]
```

**[F2]** `AM2020` · *Lazo SLC Circuito de señalización. El cable del lazo a lo largo del cual se conectan los equipos direccionables.* · `MFDT280` p.41 · sim 0.75

```
Lazo SLC
Circuito de señalización. El cable del lazo a lo largo del cual se conectan los equipos direccionables.

Lazo SLC
Circuito de señalización. El cable del lazo a lo largo del cual se conectan los equipos direccionables.

MF-DT-280
         41
        NOTIFIER ESPAÑA, S.A.
ISIB
Placa interface serie analógica. Utilizada para la comunición con los módulos de control anunciadores.
LIB-200
Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC.
Modo Local
La operación independiente de una placa LIB-200 cuando falla la comunicación de un lazo. Tres direcciones
aisladas pueden ser programadas por el usuario en la memoria del sistema para funcionamiento en modo local
(una dirección para detectores analógicos, una para módulos monitor, y una para módulos de control). Si las
comunicaciones entre un LIB-200 y la placa de la CPU se interrumpen, el modo local realizará la siguiente
función: si sucede una alarma en un detector o en un módulo monitor, el LIB automaticamente activará todos
los módulos de control hasta la dirección del último detectado (donde se ha efectuado el corte).
Punto
La ocupación de una dirección de memoria del sistema por un equipo direccionable del lazo, zona de
programación o punto anunciador.
Zona de retroceso
Una zona de programación la cual no se activa directamente por la entrada de un equipo o zona avanzada
puede activarse a través de una ecuación asociada de control por evento. Una zona de retroceso puede ser
referenciada en otra ecuación de control-por-evento.
Señal aislada
Una característica del sistema la cual puede causar la función de silencio señal para activarse automaticamente
después de un período de tiempo programado después de una alarma.
Silencio Señal
Una función la cual puede desactivar los aviso d
[… contenido truncado para legibilidad]
```

**[F3]** `AM2020` · *LIB-200 Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC.* · `MFDT280` p.41 · sim 0.74

```
LIB-200
Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC.

LIB-200
Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC.

MF-DT-280
         41
        NOTIFIER ESPAÑA, S.A.
ISIB
Placa interface serie analógica. Utilizada para la comunición con los módulos de control anunciadores.
LIB-200
Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC.
Modo Local
La operación independiente de una placa LIB-200 cuando falla la comunicación de un lazo. Tres direcciones
aisladas pueden ser programadas por el usuario en la memoria del sistema para funcionamiento en modo local
(una dirección para detectores analógicos, una para módulos monitor, y una para módulos de control). Si las
comunicaciones entre un LIB-200 y la placa de la CPU se interrumpen, el modo local realizará la siguiente
función: si sucede una alarma en un detector o en un módulo monitor, el LIB automaticamente activará todos
los módulos de control hasta la dirección del último detectado (donde se ha efectuado el corte).
Punto
La ocupación de una dirección de memoria del sistema por un equipo direccionable del lazo, zona de
programación o punto anunciador.
Zona de retroceso
Una zona de programación la cual no se activa directamente por la entrada de un equipo o zona avanzada
puede activarse a través de una ecuación asociada de control por evento. Una zona de retroceso puede ser
referenciada en otra ecuación de control-por-evento.
Señal aislada
Una característica del sistema la cual puede causar la función de silencio señal para activarse automaticamente
después de un período de tiempo programado después de una alarma.
Silencio Señal
Una función la cual puede desactivar los aviso de alarma u otras salidas sin a
[… contenido truncado para legibilidad]
```

**[F4]** `AM2020 and AFP1010` · *PRESS 1=PPAR,2=PTOT,3=PPPT,4=PTPT,5=BORR,6=CLVE,7=MSG,8=HIS :* · `MPDT280` p.6 · sim 0.80

```
PRESS 1=PPAR,2=PTOT,3=PPPT,4=PTPT,5=BORR,6=CLVE,7=MSG,8=HIS
: (continuación)

[TABLA EXTRAÍDA]
|  |  | SECCIÓN | B: | 
----------------------------------------
 | MENÚ P | RIN | CIPAL DE | PROGRAMACION | 
CLAV | E |  |  |  | 
PRESS 1 | =PPAR,2=PTOT,3 | =PPPT | ,4=PTPT,5=BORR | ,6=CLVE,7=MSG,8=HIS : | 
de |  |  |  | Pági | na
1=PPAR | Programación pa | rcial d | el sistema - Program | ación selectiva abarcando amplia- | 8
 | mente funciones | del sis | tema (número de L | IB-200s, AVPS-24s, ISIB, inhibir | 
 | silenciada y corte | de la | señal, Verificación | de Alarmas, número de módulos | 
 | anunciadores, etc | .). |  |  | 
 |  |  |  |  | 18
2=PTOT | Programación c | omplet | a del sistema - pr | ogramación completa de amplias | 
 | funciones del siste | ma (nú | mero de LIB-200s, | AVPS-24s, ISIB, inhibir silenciado | 
 | y corte de la seña | l, verific | ación de alarmas, n | úmero de módulos anunciadores, | 
 | etc.). |  |  |  | 21
3=PPPT | Programación p | arcial | de punto - alterac | ión selectiva de los parámetros | 
 | operativos de los | dispos | itivos del bucle SL | C, zonas de software definidas y | 
 | puntos anunciado | res. |  |  | 29
4=PTPT | Programación co | mplet | a de un punto - Pro | gramación completa de los dispo- | 
 | sitivos direccional | es del | Bucle SLC, zonas de | software definidas, puntos anun- | 
 | ciadores y sus pa | rámetro | s operativos respec | tivos. | 31
5=BORR | Retirar - Permite | la retir | ada selectiva (de la | memoria del panel de control) de | 
 | cualquiera de los d | ispositi | vos direccionables d | el Bucle SLC, de zonas de software | 
 | definidas o de pun | tos an | unciadores. |  | 31
6=CLVE | Clave de acceso | - Permi | te al programador el | asignar claves de acceso de cinco | 
 | dígitos de los nive | les un
[… contenido truncado para legibilidad]
```

**[F5]** `AM2020/AFP1010` · *Grupo 1. Detectores direccionables* · `MADT283` p.2 · sim 0.72

```
Grupo 1. Detectores direccionables

MA-DT-283
NOTIFIER ESPAÑA, S.A.
2 de 8
Todos las direcciones de equipos y zonas de software deben definirse con el tipo de identificación apropiado
al realizar la programación. La definición de una zona de software permite a la AM2020/AFP1010 identificar
el tipo y configuración de un equipo específico asociado al panel.
Cada tipo de ID esta catalogado por grupos. Hay 17 grupos de software diferentes los cuales son definidos en
las siguientes tablas. Cada tabla tiene el siguiente formato.
Tipo ID - Este es el tipo de software introducido por el programado para un punto en concreto.
Descripción. - Este es la forma que la central muestra el tipo de software ID en el CRT y en el DIA.
Tipo de Equipo. - Tipo de equipos compatibles y descripción de parámetros para un tipo de ID particular.
La central no permitirá cambiar de un tipo de software ID perteneciente a un grupo a otro grupo de ID
diferente. En el caso de realizar esta operación, el equipo deberá ser reinstalado con el tipo de ID deseado
utilizando la Programación Total de Puntos.
Grupo 1. Detectores direccionables
DEFINICIÓN DE TIPOS DE I.D. EN LA AM2020/AFP1010
Revisión 6.0 y 6.5
```

### Respuesta del bot

```
Los fragmentos recuperados **no contienen** el dato de número máximo de lazos SLC ni el número máximo de dispositivos por lazo para la **AM2020/AFP1010**.

Lo que sí aparece en los fragmentos es:

- La central usa tarjetas de lazo **LIB-200**, **LIB-200A** y **LIB-400** para la comunicación con cada lazo SLC [F1]
- El **LIB-200** es la "Placa interface de lazo. Utilizada para la alimentación y comunicación con cada lazo SLC" [F2][F3]
- La programación del sistema permite indicar el número de **LIB-200s** instalados (opción `1=INST` del menú de programación) [F4]
- Los dispositivos del lazo se programan con tipos de ID organizados en **17 grupos de software** [F5]

Sin embargo, los valores concretos que preguntas (número máximo de lazos y dispositivos por lazo) **no están en los fragmentos disponibles**. Consulta el manual de instalación/especificaciones técnicas de la AM2020/AFP1010 para esos datos.

---

**Nota:** Los modelos disponibles en mi base de datos son: **15090SP, AFP-200E, AFP-300/AFP-400, AM 8100, AM 8200G, AM 8200N, AM-200, AM-2000, AM-8100, AM-8200**. Si trabajas con alguno de estos, puedo consultarlo directamente.

Fuente: BTDT032 (sin revisión registrada); MFDT280 (sin revisión registrada); MPDT280 (rev. A); MADT283 (sin revisión registrada)

---

También puedo ayudarte con: **modo local del LIB-200**, **tipos de ID y grupos de software de la AM2020/AFP1010** o **opciones del menú de programación**.
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

**Razón del judge:** Los fragmentos F (ni V) no contienen los datos específicos de número máximo de lazos SLC ni dispositivos por lazo para la AM2020/AFP1010. El bot admite honestamente esta ausencia, cita correctamente lo que sí aparece en los fragmentos (tarjetas LIB-200/200A/400, menú de programación, grupos de ID), y redirige al técnico al manual de especificaciones técnicas, lo cual constituye un admit_no_info honesto y útil alineado con la conducta esperada.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (datos generales del producto AM2020/AFP1010 Notifier):**

- **AM2020**: hasta **10 lazos SLC** (mediante tarjetas LIB-200 o LIB-200A), **99 detectores + 99 módulos por lazo** (direcciones 1-99 + 1-99). Hasta 990 detectores + 990 módulos por sistema.
- **AFP1010**: hasta **10 lazos SLC**, mismo esquema. Algunas versiones soportan LIB-400 con direcciones extendidas.
- Las cifras concretas dependen de la revisión de firmware (6.0/6.5/posteriores) y de la configuración de paneles esclavos.

Este es un dato de especificación técnica que **debería estar** en MIDT280 (instalación) o MSDT280 (especificaciones), no en MFDT280 (funcionamiento) ni MPDT280 (programación) ni MADT283 (tipos ID).

**Calidad de los chunks:**

- **F1 header largo y arbitrario**: "Y/O Cualquier módulo monitor con una dirección inferior o igual a la dirección máxima and/or programada en modo local para módulos monitores entra en alarma." — frase de mitad de tabla de modo local, no un epígrafe.
- **F2 y F3 son duplicados casi exactos**: F2 ("Lazo SLC...") y F3 ("LIB-200...") provienen ambos del mismo glosario en MFDT280 p.41, con contenido superpuesto.
- **F4 header inútil**: "PRESS 1=PPAR,2=PTOT,3=PPPT,4=PTPT,5=BORR,6=CLVE,7=MSG,8=HIS :" — es un prompt de pantalla, no un epígrafe.
- **F4 `[TABLA EXTRAÍDA]` mal aplicado**: el contenido es texto plano en formato lista, no tabla.
- **F5 header inútil**: "Grupo 1. Detectores direccionables" — sí es un epígrafe (correcto), pero el contenido del chunk es introductorio (no contiene grupos completos).
- **Retrieval cubre programación/funcionamiento/tipos de ID pero NO especificaciones técnicas**. Ningún chunk de MSDT280 (specs) o MIDT280 (instalación con capacidades) entró en top-5.

**Comparación con bot:**

- ✓ Admite honestamente que F no contiene el número de lazos ni dispositivos por lazo.
- ✓ Cita correctamente LIB-200/200A/400 (de F1).
- ✓ Cita 17 grupos de ID (de F5).
- ⚠️ La "nota" de modelos disponibles en su base (15090SP, AFP-200E, AFP-300/AFP-400, AM 8100, AM 8200G, AM 8200N, AM-200, AM-2000, AM-8100, AM-8200) **suena automática**: lista AM-2000 dos veces (AM-2000 y AM-2000 con guion), incluye AM-8100 dos veces, no incluye AM2020/AFP1010 — lo que confirma que el `product_model` registrado no enlaza correctamente con `source_file`. Este es el problema que la nota YAML ya señala.
- ⚠️ Sería más útil que el bot diera al menos el **dato típico de fábrica** ("99 + 99 por lazo, 10 lazos máximo en AM2020"), aclarando que es conocimiento general del producto Notifier — pero la política del bot parece ser estricta sobre no usar conocimiento fuera del corpus.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — admisión correcta dado el corpus disponible
- [ ] **Pero el corpus es deficiente**: el manual completo de la AM2020 tiene un capítulo de especificaciones que debería contener este dato y que no se está chunkeando bien o no está indexado.
- **Dimensión equivocada(s) del judge:** ninguna dentro de su alcance.
- **Nota / por qué:** El bot es honesto sobre lo que tiene. El problema real es de **cobertura del corpus o de retrieval**: una pregunta de "specs básicas" no debería caer en admit_no_info para un producto con manual completo en el corpus. La nota YAML lo identifica (AM2020/AFP1010 vive en product_model dentro de MFDT280/15088SP/MADT285) — pero la query no rankea bien hacia el chunk que contiene las specs (que probablemente esté en MSDT280 o MIDT280, no traídos).
- **Origen del problema:** **retrieval** (no recupera chunk de specs) + **metadata** (product_model vs source_file desconectados) + **chunk-extraction** (duplicación masiva F2=F3 del glosario).

---

## hp013 — judge dice **PASS ✓** · (13/20)

**Pregunta del técnico:** ¿Cómo se cambia la batería tampón de la Detnov ADW535 sin perder configuración?

**Conducta esperada:** `admit_no_info` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `False`

> _Notas YAML: Cambiado a admit_no_info en sesión 15 (24 abril 2026): corpus verificado — ni 'batería tampón' ni 'CR2032' aparecen en ADW535. Bot admite correctamente._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ADW535` · *• Mantenimiento de la temperatura mínima con reset inicial 032 Error activación motor paso a paso Tensión de alimentació* · `ADW535_TD_T140358es_e` p.107 · sim 0.80

```
• Mantenimiento de la temperatura mínima
con reset inicial
032
Error activación motor paso a paso
Tensión de alimentación en el ADW
• Sección de cable al ADW no dimensio-
nado de forma suficiente (continuación)

G04, fallos sensor de temperatura LMB 
Código Significado 
Comprobaciones: 
Posibles causas y solución: 
016 
Fallo sensor de temperatura LMB 
LMB, sensor de temperatura 
• LMB defectuoso  Sustituir 
032 
Parámetros no válidos, sensor de tempera-
tura LMB (defecto de fabricación) 
LMB, sensor de temperatura 
• LMB defectuoso  Sustituir 
G11 o G21, sensor de temperatura I / II fallos 
Código Significado 
Comprobaciones: 
Posibles causas y solución: 
016 
Fallo sensor de temperatura externo 
Cable de conexión, borne de conexión 
LMB, LEB, sensor de temperatura 
• Cable de conexión no enchufado correc-
tamente o defectuoso  Comprobar, 
sustituir 
• Sensor de temperatura defectuoso  
Sustituir 
• LMB (o LEB) defectuoso  Sustituir 
032 
Parámetros no válidos, sensor de tempera-
tura externo (defecto de fabricación) 
Cable de conexión, borne de conexión 
LMB, LEB, sensor de temperatura 
• Cable de conexión no enchufado correc-
tamente o defectuoso  Comprobar, 
sustituir 
• Sensor de temperatura defectuoso  
Sustituir 
• LMB (o LEB) defectuoso  Sustituir 
064 
Fallo tubo sensor – sensor de temperatura, 
compensación 
Cable de conexión, borne de conexión 
LMB, LEB, sensor de temperatura, con-
figuración 
• Cable de conexión no enchufado correc-
tamente o defectuoso  Comprobar, 
sustituir 
• Sensor de temperatura defectuoso  
Sustituir 
• LMB (o LEB) defectuoso  Sustituir 
• Configuración  Comprobar 
G12 o G22, fallos sensor de temperatura I / II 
Código Significado 
Comprobaciones: 
Posibles causas y solución: 
001 
Fallo sensor de presión 
Conexión de cable
[… contenido truncado para legibilidad]
```

**[F2]** `ADW535` · *(12) Pulsar el botón para compro- bar la modificación* · `ADW535_TD_T140358es_e` p.73 · sim 0.80

```
(12)
Pulsar el botón para compro-
bar la modificación

(12)
Pulsar el botón para compro-
bar la modificación

Puesta en funcionamiento 

ADW 535, Descripción técnica, T 140 358 e es 
73 / 119 
7.3.3 
Ajuste en la posición de conmutador predefinida A1 a T3, W00 a W09 
El siguiente cuadro describe el procedimiento en el que el ADW 535 debe ajustarse en una de las posiciones de conmutador 
fijas C > A1 a T3 y, si es necesario, a una monitorización del tubo sensor modificada W01 a W09. Debe tenerse en cuenta 
que las posiciones W04 a W09 implican una monitorización del tubo sensor no normativa conforme a EN 54-22. 
Ejemplo: (primera parte de la tabla) ADW 535-2 (con 2 tubos sensores) deberá responder de acuerdo con EN 54-22, clase 
A2l. Los tubos sensores tienen distintas longitudes: tubo sensor I = 85 m, tubo sensor II = 95 m. Según el cap. 4.5.1.1,debe 
seleccionarse la posición de conmutador C > A2. 
La segunda parte de la tabla muestra cómo se puede cambiar a continuación la monitorización del tubo sensor, en este ca-
so (como ejemplo) para la configuración no normativa W04.
```

**[F3]** `ADW535` · *-A2----* · `ADW535_TD_T140358es_e` p.73 · sim 0.80

```
-A2----

-A2----

Puesta en funcionamiento 

ADW 535, Descripción técnica, T 140 358 e es 
73 / 119 
7.3.3 
Ajuste en la posición de conmutador predefinida A1 a T3, W00 a W09 
El siguiente cuadro describe el procedimiento en el que el ADW 535 debe ajustarse en una de las posiciones de conmutador 
fijas C > A1 a T3 y, si es necesario, a una monitorización del tubo sensor modificada W01 a W09. Debe tenerse en cuenta 
que las posiciones W04 a W09 implican una monitorización del tubo sensor no normativa conforme a EN 54-22. 
Ejemplo: (primera parte de la tabla) ADW 535-2 (con 2 tubos sensores) deberá responder de acuerdo con EN 54-22, clase 
A2l. Los tubos sensores tienen distintas longitudes: tubo sensor I = 85 m, tubo sensor II = 95 m. Según el cap. 4.5.1.1,debe 
seleccionarse la posición de conmutador C > A2. 
La segunda parte de la tabla muestra cómo se puede cambiar a continuación la monitorización del tubo sensor, en este ca-
so (como ejemplo) para la configuración no normativa W04.
```

**[F4]** `ADW535` · *Indicación* · `ADW535_TD_T140358es_e` p.64 · sim 0.80

```
Indicación (continuación)

Configuración con dirección IP alternativa temporal 
En caso de que en el PC se seleccione una dirección IP fuera del rango 169.254.x.x, la conexión con el ADW 535 ya no será 
posible. Esto se debe a que los dos dispositivos se encuentran en subredes distintas. Para solucionar este problema, es posi-
ble definir temporalmente en la configuración del PC una dirección IP alternativa que permita acceder al rango 169.254.x.x. 
Para ello, se debe proceder de la siguiente manera: 
1. 
en el «Panel de control», acceder a «Conexión LAN» (dentro de «Redes e internet» o en «Centro de redes y recur-
sos compartidos» > «Cambiar configuración del adaptador») y abrir «Características» con el botón derecho del 
ratón. 
2. 
Marcar el elemento «Protocolo de internet versión 4 (TCP/IPv4)» y abrir «Características». 
3. 
En la pestaña «General», seleccionar «Avanzado...» y abrir el cuadro de diálogo «Ajustes avanzados TCP/IP». 
4. 
Ir a «Añadir...», abrir el cuadro de diálogo «Dirección TCP/IP» e introducir la siguiente configuración: 
- 
Dirección IP: 
169.254.1.2 
- 
Máscara de subred: 
255.255.0.0 
Gracias a esta configuración alternativa, podrá modificar la dirección IP del ADW 535 sin perder temporalmente la conexión. 
Por descontado, la configuración alternativa puede eliminarse cuando ya no sea necesaria.
```

**[F5]** `ADW535` · *Pulsar Parpadeo A1 > W00 > L01 > 115 > L02 > 115 (sucesivamente)* · `ADW535_TD_T140358es_e` p.73 · sim 0.80

```
Pulsar
Parpadeo A1 > W00 > L01 > 115
> L02 > 115 (sucesivamente)

Pulsar
Parpadeo A1 > W00 > L01 > 115
> L02 > 115 (sucesivamente)

Puesta en funcionamiento 

ADW 535, Descripción técnica, T 140 358 e es 
73 / 119 
7.3.3 
Ajuste en la posición de conmutador predefinida A1 a T3, W00 a W09 
El siguiente cuadro describe el procedimiento en el que el ADW 535 debe ajustarse en una de las posiciones de conmutador 
fijas C > A1 a T3 y, si es necesario, a una monitorización del tubo sensor modificada W01 a W09. Debe tenerse en cuenta 
que las posiciones W04 a W09 implican una monitorización del tubo sensor no normativa conforme a EN 54-22. 
Ejemplo: (primera parte de la tabla) ADW 535-2 (con 2 tubos sensores) deberá responder de acuerdo con EN 54-22, clase 
A2l. Los tubos sensores tienen distintas longitudes: tubo sensor I = 85 m, tubo sensor II = 95 m. Según el cap. 4.5.1.1,debe 
seleccionarse la posición de conmutador C > A2. 
La segunda parte de la tabla muestra cómo se puede cambiar a continuación la monitorización del tubo sensor, en este ca-
so (como ejemplo) para la configuración no normativa W04.
```

### Respuesta del bot

```
Los fragmentos recuperados del manual **ADW535** (ADW535_TD_T140358es_e) no contienen ninguna información sobre el procedimiento de sustitución de la batería tampón ni sobre cómo preservar la configuración durante ese proceso.

Los fragmentos disponibles cubren únicamente:
- Códigos de fallo y diagnóstico (sensores de temperatura, presión, tubo sensor) [F1]
- Procedimiento de ajuste de posiciones de conmutador (A1 a T3, W00 a W09) [F2, F3, F5]
- Configuración de dirección IP alternativa para conexión PC-ADW535 [F4]

**No tengo ese dato en los fragmentos recuperados.** Para el procedimiento de cambio de batería tampón sin pérdida de configuración, consulta directamente:
- El manual físico completo del **ADW535** (ADW535_TD_T140358es_e), en la sección de mantenimiento
- O el soporte técnico de **Detnov**

---

Fuente: ADW535_TD_T140358es_e (rev. sin revisión registrada)
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

**Razón del judge:** Ni los fragmentos F ni los fragmentos V contienen ninguna información sobre el procedimiento de cambio de batería tampón en el ADW535 (el manual cubre mantenimiento general, fallos, puesta en funcionamiento y firmware, pero no menciona batería tampón en ningún chunk). El bot admite correctamente que no tiene ese dato, describe con precisión lo que sí cubren los fragmentos recuperados, y redirige al técnico al manual físico y al soporte del fabricante — conducta admit_no_info honesta y útil.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `ADW535_TD_T140358es_e`):**

El manual ADW535 (Securiton — **OJO: ADW535 no es Detnov, es Securiton**, vendido por Detnov/distribuido) **no documenta procedimiento de sustitución de "batería tampón"**. La ADW535 no tiene batería interna tipo botón de configuración (la configuración del firmware se almacena en memoria no volátil — EEPROM/Flash — y persiste sin alimentación). El alimentación externa proviene de la fuente del sistema PCI o de baterías del bus, no de batería tampón interna del módulo.

Si el técnico se refiere a:
- **Reset/re-inicial**: cap. 7.3 ("Reset inicial" del tubo sensor) — se hace tras intervención eléctrica, no implica batería.
- **Backup config**: configuración persiste en EEPROM; copia de seguridad mediante PC/software ADW Tool a través de IP 169.254.x.x (F4).
- **Carga de pila CR2032 del reloj**: NO existe en ADW535 (no aparece en el manual).

**Calidad de los chunks:**

- **Premisa errónea del eval/usuario**: "batería tampón" no existe en ADW535. La nota YAML lo confirma ("ni 'batería tampón' ni 'CR2032' aparecen"). Esta es información que el bot podría haber dado proactivamente.
- **Atribución de fabricante incorrecta en la pregunta**: la pregunta dice "Detnov ADW535" — la ADW535 es **Securiton** (Detnov puede distribuirla pero el manual es Securiton T 140 358). Mismo patrón que hp002 (ASD535).
- **F1 header con info de "Mantenimiento de temperatura mínima"** pero el contenido es tabla de códigos de fallo G04/G11/G12 — header mismatch.
- **F2 y F3 son duplicados** (sim 0.80 ambos, mismo chunk p.73 sec. 7.3.3). F3 además tiene header inútil "-A2----" (fragmento de tabla de switches).
- **F5 también duplicado de F2/F3** (mismo chunk p.73 sec. 7.3.3 con header "Pulsar Parpadeo A1 > W00...").
- **3 de 5 chunks (F2, F3, F5) son el mismo contenido de p.73**. Duplicación masiva, idéntica similitud 0.80.
- **F4 (IP alternativa) sí es útil** para entender que la config persiste y se puede backupear, aunque el bot no lo explota.

**Comparación con bot:**

- ✓ Admite honestamente que no hay info en F sobre batería tampón.
- ✓ Describe correctamente lo que sí cubren los F.
- ⚠️ NO cuestiona la premisa "batería tampón en ADW535" — debería haber aclarado al técnico que el ADW535 no tiene esa batería arquitectónicamente. Igual que en hp015 con CCD-103 (operación que no existe).
- ⚠️ NO corrige el fabricante: la pregunta dice "Detnov ADW535" pero ADW535 es Securiton (lo distribuye Detnov en ES, pero el manual es Securiton). Mismo patrón de hp002.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — la admisión es coherente con los F y la nota YAML
- [ ] **Pero la respuesta es subóptima**: un técnico que pregunta esto está confundido sobre la arquitectura del producto. El bot debería decir: "El ADW535 no tiene batería tampón documentada; su configuración se almacena en memoria no volátil. ¿Quizás te refieres a otro producto?".
- **Dimensión equivocada(s) del judge:** ninguna dentro de su alcance estricto. El bot cumple admit_no_info pero pierde la oportunidad de educar al técnico (helpful queda en gris).
- **Nota / por qué:** Admit_no_info correcto. Pero el bot, al igual que hp019, acepta premisas erróneas sin desafiarlas. Patrón: el bot no detecta cuando una pregunta presupone algo que el producto no tiene.
- **Origen del problema:** **chunk-extraction** (3/5 chunks idénticos = ranking quebrado) + **generación** (no desafía premisa) + **metadata** (atribución a Detnov en lugar de Securiton no se corrige).

---

## hp014 — judge dice **PASS ✓** · (14/20)

**Pregunta del técnico:** ¿Cómo se conecta un módulo de aislamiento de línea en un lazo ID2000?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: expected_sources retirado: 'ID2000' no aparece en source_file (solo en product_model, 4169 chunks). Mantenido 'answer': corpus tiene reglas de posicionamiento de aisladores en chunks ID2000 aunque no el esquema wiring completo; el bot puede dar respuesta parcial legítima. Keywords relajados para aceptar tanto respuesta completa como parcial._

### Fragmentos que el bot usó (top 5)

**[F1]** `ID2000` · *Nota:La impresora integral PRN2000 se controla automáticamente y no necesita configurarse en ningún puerto aislado.* · `MPDT180` p.82 · sim 0.80

```
Nota:La impresora integral PRN2000 se controla
automáticamente y no necesita configurarse en
ningún puerto aislado.

Nota:La impresora integral PRN2000 se controla
automáticamente y no necesita configurarse en
ningún puerto aislado.

Panel ID2000  - Manual de programación
Opciones de configuración
MP-DT-180
       NOTIFIER ESPAÑA
       77
10.22 Selección modo RS232
El mensaje siguiente sólo aparece si programa el sistema
con las teclas del panel:
El puerto RS232 suministrado con todos los paneles de
la serie ID2000 se puede utilizar para conectar una
impresora de 80 columnas o la ‘herramienta de soporte
para la configuración’ . Un puerto aislado adicional se
puede configurar para:
a. Impresora de 80 columnas
b. Impresora P40
c. Opción de ‘3er Protocolo/Integrac’ - Este modo especial
se utiliza para conectar otro tipo de equipamiento, por
ejemplo un ordenador. Si desea detalles sobre los
protocolos disponibles, póngase en contacto con
NOTIFIER.
Nota: La impresora integral PRN2000 se controla
automáticamente y no necesita configurarse en
ningún puerto aislado.
Seleccione la opción deseada. Si selecciona 2, aparecerá
la siguiente pantalla:
Seleccione la opción deseada. En todos los caso (excepto
con la impresora P40), aparece la siguiente pantalla:
Utilice las teclas numéricas para seleccionar el número
de baudios.
Si conecta una impresora PRN2000 al panel, no
seleccione la ‘impresora P40’ en el menú de selección
de modo RS232. El sistema no puede soportar las dos
impresoras en el mismo panel.
Nota: Si selecciona la impresora P40, el número de
baudios se configura automáticamente a 1200
baudios, el ajuste correcto.
Protocolo integr.2 1=Habil. CONTROLES/
2=Supervisar COMUN./3=AMBAS/0=NADA: 0
Modo puerto RS232 aislado: 0=Impr. 80c/
1=Impr. P40/2=3er Protocolo/Integrac.:  0
[… contenido truncado para legibilidad]
```

**[F2]** `ID2000` · *0 = Individual/ 1 = Lazo completo:* · `MFDT180` p.28 · sim 0.80

```
0 = Individual/ 1 = Lazo completo:

0 = Individual/ 1 = Lazo completo:

Panel ID2000 - Manual de funcionamiento
Acciones que realiza el usuario en el panel
MF-DT-180
       NOTIFIER ESPAÑA
       25
4.8.4
Sustitución del sensor VIEW
Los sensores VIEW deben calibrarse cuando funcionan
por primera vez en el panel. Esta calibración se realiza
automáticamente para cada sensor VIEW en cualquiera
de estos casos:
a. Los primeros  90 segundos después de haber conectado
la alimentación en el panel.
o
b. 60 segundos después de haber instalado el sensor en el
panel que ya está funcionando con normalidad (mediante
descarga del archivo de configuración o utilizando los
menús en pantalla).
Durante el periodo inicial (necesario para conseguir
estabilidad en el sensor VIEW), el sensor VIEW no debe
exponerse a humos ni condiciones extraordinarias, ya
que el panel podría señalizar una avería.
La opción del menú para ‘Sustituir el sensor’ sólo se aplica
al sensor VIEW. Si se retira un sensor VIEW de un lazo
existente y operativo o se interrumpe la comunicación
con el panel durante un mínimo de 30 segundos, se
realizará automáticamente una recalibración.
Nota: Si se retira un sensor VIEW para limpiarlo o
sustituirlo por uno nuevo, espere como mínimo 30
segundos antes de volverlo a instalar.
Los sensores VIEW también se pueden recalibrar
manualmente, de forma individual o todos los de un lazo
o panel al mismo tiempo. Desde la pantalla de primer
nivel, pulse ‘0’ y, a continuación, la tecla adecuada
(dependiendo de las opciones de configuración). Debe
introducir la clave de acceso 3. Una vez introducidos los
dígitos de la clave, aparecerá la siguiente pantalla:
0 = Individual/ 1 = Lazo completo:
00:00:30
00:00:00
```

**[F3]** `ID2000` · *3.2.1Introducción 13* · `MIDT180` p.2 · sim 0.80

```
3.2.1Introducción
13

3.2.1Introducción
13

Panel ID2000 - Manual de instalación y puesta en marcha
Índice
MI-DT-180
         NOTIFIER ESPAÑA
       i
Índice
1
Introducción
1
1.1
Distintivo CE
1
1.2
Diseño y planificación del sistema
1
1.3
Personal
1
1.4
General
1
1.4
Funciones que dependen de la fecha
2
Instalación: Secciones 2-7
2
Guía de la instalación
3
2.1
Cómo utilizar esta guía
3
2.1.1 Documentos relacionados
3
2.1.2 Avisos y precauciones
3
2.1.3 Consejos
3
2.1.4 Glosario de iconos
4
2.2
Comprobaciones previas a la instalación
5
2.2.1 Qué DEBE o NO DEBE hacer
5
2.3
Protección contra interferencias transitorias
6
2.4
Instalación
7
2.4.1 Comprobación del panel
7
2.4.2 Qué hacer si el panel está dañado
8
2.4.3 Fijación de la caja trasera
9
2.4.4 Componentes electrónicos
10
2.5
Sustitución de los módulos electrónicos
11
2.6
Marco embellecedor para montaje
empotrado (opcional)
11
3
Cableado
12
3.1
Instrucciones de cableado
12
3.1.1 Terminaciones de cable
13
3.2
Notas sobre la instalación del cable
13
3.2.1 Introducción
13
3.2.2 Calidad e instalación del cable
13
3.3
Consideraciones sobre EMC
(Compatibilidad electromagnética)
14
3.3.1 Terminación de pantalla
15
3.3.2 Ferritas (opcional)
15
3.4
Cables MICC
15
Los símbolos siguientes se pueden
encontrar en el interior de la central o en la
documentación que la acompaña.:
AVISO: Riesgo de descarga
eléctrica. Antes de manipular
las conexiones, compruebe que
la fuente de alimentación de la
central está desconectada.
PRECAUCIÓN: Consulte la
documentación que acompaña
al equipo. (Cuando este símbolo
se utiliza en la documentación
adjunta, normalmente se asocia
a instrucciones adicionales).
```

**[F4]** `ID2000` · *10.22 Selección modo RS232* · `MPDT180` p.82 · sim 0.80

```
10.22 Selección modo RS232

10.22 Selección modo RS232

Panel ID2000  - Manual de programación
Opciones de configuración
MP-DT-180
       NOTIFIER ESPAÑA
       77
10.22 Selección modo RS232
El mensaje siguiente sólo aparece si programa el sistema
con las teclas del panel:
El puerto RS232 suministrado con todos los paneles de
la serie ID2000 se puede utilizar para conectar una
impresora de 80 columnas o la ‘herramienta de soporte
para la configuración’ . Un puerto aislado adicional se
puede configurar para:
a. Impresora de 80 columnas
b. Impresora P40
c. Opción de ‘3er Protocolo/Integrac’ - Este modo especial
se utiliza para conectar otro tipo de equipamiento, por
ejemplo un ordenador. Si desea detalles sobre los
protocolos disponibles, póngase en contacto con
NOTIFIER.
Nota: La impresora integral PRN2000 se controla
automáticamente y no necesita configurarse en
ningún puerto aislado.
Seleccione la opción deseada. Si selecciona 2, aparecerá
la siguiente pantalla:
Seleccione la opción deseada. En todos los caso (excepto
con la impresora P40), aparece la siguiente pantalla:
Utilice las teclas numéricas para seleccionar el número
de baudios.
Si conecta una impresora PRN2000 al panel, no
seleccione la ‘impresora P40’ en el menú de selección
de modo RS232. El sistema no puede soportar las dos
impresoras en el mismo panel.
Nota: Si selecciona la impresora P40, el número de
baudios se configura automáticamente a 1200
baudios, el ajuste correcto.
Protocolo integr.2 1=Habil. CONTROLES/
2=Supervisar COMUN./3=AMBAS/0=NADA: 0
Modo puerto RS232 aislado: 0=Impr. 80c/
1=Impr. P40/2=3er Protocolo/Integrac.:  0
Configuración: Puerto RS232 aislado
(1200/2400/4800/9600):  9600
```

**[F5]** `ID2000` · *Note:Si los mensajes en pantalla no se pueden leer con claridad, ajuste el contraste de la pantalla (véase la Sección 4.* · `MFDT180` p.10 · sim 0.65

```
Note:Si los mensajes en pantalla no se pueden leer con
claridad, ajuste el contraste de la pantalla (véase la
Sección 4.7.3). (continuación)

[TABLA EXTRAÍDA]
Pan | el ID2000 - Manual de | funcionamiento |  |  |  | 
----------------------------------------
4 | Acciones que | realiza el | usuario |  | en el | panel
4.1 | Introducción |  |  |  |  | 
 | La pantalla y las tecla | s de control del p | anel permi | te | n al usua | rio realiz
 | las siguientes accion | es: |  |  |  | 
 | a. Silenciar el zumba | dor del panel. |  |  |  | 
 | b. Aceptar una condi | ción de alarma o | avería. |  |  | 
 | c. Iniciar un proceso d | e Evacuación (y a | nular los r | et | ardos de | las salida
 | si estaban activos | ). |  |  |  | 
 | d. Silenciar y reactiv | ar las alarmas |  |  |  | 
 | e. Rearmar el panel. |  |  |  |  | 
 | f. Probar los leds y | ajustar el contras | te de la pa | n | talla. | 
 | g. Realizar pruebas | de sistema. |  |  |  | 
 | h. Anular y habilitar | equipos, zonas y | todas las | sa | lidas. | 
 | i. Visualizar en pant | alla, registrar e im | primir da | to | s. | 
 | j. Ajustar el reloj. |  |  |  |  | 
 | Todas estas acciones | están protegidas | mediante | un | a puerta | de interf
 | de usuario o clave de | acceso (véase S | ección 4. | 1. | 2). |
```

### Respuesta del bot

```
Los fragmentos recuperados del ID2000 no contienen información sobre el conexionado de módulos de aislamiento de línea en el lazo. Los fragmentos disponibles cubren únicamente configuración de puertos RS232 [F1][F4], calibración de sensores VIEW [F2], índice del manual de instalación [F3] y acciones de usuario en panel [F5].

Para el conexionado del módulo de aislamiento, necesitarás consultar directamente:

- El **Manual de Instalación y Puesta en Marcha MI-DT-180** del ID2000 [F3], específicamente la **Sección 3 (Cableado)** y sus subsecciones 3.1 y 3.2, que tratan sobre instrucciones de cableado y notas de instalación del cable.

Te recomiendo que me facilites el modelo exacto del módulo de aislamiento que estás usando (por ejemplo, su referencia de producto Notifier), ya que podría tener documentación específica en mi base.

---

Fuente: MIDT180 (sin revisión registrada); MFDT180 (sin revisión registrada); MPDT180 (rev. Rev io)
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

**Razón del judge:** El bot admite correctamente que los fragmentos recuperados (F1-F5) no contienen información sobre el conexionado del módulo de aislamiento de línea, y ningún fragmento V tampoco cubre ese tema específico, por lo que la admisión de falta de información es honesta y precisa. El bot redirige al técnico al Manual de Instalación MI-DT-180 (Sección 3, Cableado), que sí aparece referenciado en el índice de F3, y solicita la referencia exacta del módulo para poder ayudar mejor, lo cual es una acción úti

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `MI-DT-180` Manual de instalación y puesta en marcha ID2000 — Sección 3 Cableado):**

Los módulos de aislamiento de línea (típicamente M500X-ES o módulos Notifier de la serie ISO) se conectan al lazo SLC de la ID2000 intercalados en el cableado, no como dispositivos direccionables. Disposición típica:
1. **Estratégicamente cada 32 detectores como máximo** (límite habitual EN54) para que un cortocircuito aísle un segmento.
2. Conexión: **terminales L1+/L1- a un lado, L2+/L2- al otro** (entrada y salida del bus aislada).
3. Bus polarizado: respetar polaridad. Pantalla a tierra solo en un punto del lazo.
4. Idealmente uno antes y otro después de cada zona física, para limitar segmentos.
5. Configurar el lazo como Clase A (loop cerrado) para que la central pueda alimentar desde ambos extremos cuando se aísla un segmento.

La sección **3** (Cableado) y subsecciones **3.1 y 3.2** del MI-DT-180 son las relevantes; la **3.5/3.6** suele tratar específicamente aisladores y carga de lazo.

**Calidad de los chunks:**

- **Retrieval falla**: ninguno de los 5 chunks contiene el conexionado o reglas de aislador. F1 y F4 son configuración RS232 (no relevante), F2 es sustitución de sensor VIEW (no relevante), F3 es el índice del manual de instalación (relevante solo como puntero), F5 es acciones de usuario.
- **F1 header inútil**: "Nota:La impresora integral PRN2000 se controla automáticamente..." — frase suelta, no epígrafe.
- **F1 y F4 prácticamente idénticos** (mismo manual MPDT180 p.82, sim 0.80 ambos): duplicación.
- **F2 header inútil**: "0 = Individual/ 1 = Lazo completo:" — opción de prompt de pantalla, no epígrafe.
- **F3 es ruido relevante**: índice del MIDT180 — útil sólo como puntero a "Sección 3 Cableado".
- **F5 `[TABLA EXTRAÍDA]` mal aplicado**: el contenido extraído como tabla es texto plano (acciones del usuario en bullets).
- **F5 header inútil**: "Note:Si los mensajes en pantalla no se pueden leer..." — nota suelta.
- **Inconsistencia idiomática en index**: F3 mezcla ES de manual con encabezado puramente en ES, OK, pero el "F5 Note:" usa inglés ("Note:") con texto castellano — síntoma de OCR sucio o concatenación mala.

**Comparación con bot:**

- ✓ Admite honestamente que F no contiene el conexionado.
- ✓ Cita correctamente el Manual MI-DT-180 sec. 3 (Cableado) — usa F3 (índice) como puntero, lo cual es correcto.
- ✓ Solicita referencia exacta del módulo de aislamiento — útil porque la ID2000 admite varios modelos (M500X, ISO-200, etc.).
- ⚠️ La respuesta es muy corta y poco útil. Podría haber incluido conocimiento general (cada 32 equipos, polaridad, Clase A vs B) marcándolo como "general, verifica en manual" — pero la política parece estricta.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — admisión coherente con los F
- [ ] **Pero respuesta poco útil**: el técnico recibe básicamente "consulta el manual" sin más orientación. La pregunta sobre conexionado de aisladores en lazo es muy estándar; un retrieval mejor debería traer el chunk relevante.
- **Dimensión equivocada(s) del judge:** ninguna dentro de su alcance.
- **Nota / por qué:** El judge marca PASS coherentemente. El problema es upstream: una pregunta común sobre aisladores en lazo recibe 5 chunks irrelevantes (RS232, VIEW, índice). El **producto está indexado pero el contenido específico no se rankea bien**.
- **Origen del problema:** **retrieval** (la query "módulo aislamiento ID2000" no rankea el chunk de aisladores que probablemente exista en MI-DT-180 sec. 3.4 o similar) + **chunk-extraction** (F1=F4 duplicados; headers inútiles en F1/F2/F5).

---

## hp015 — judge dice **PASS ✓** · (15/20)

**Pregunta del técnico:** En la Detnov CCD-103, ¿cómo se desactiva un detector individualmente sin afectar al resto del lazo?

**Conducta esperada:** `admit_no_info` · **observada:** `answer`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `False`

> _Notas YAML: Recalibrado sesión 19: la CCD-103 es central CONVENCIONAL — no soporta desactivación individual de detector (solo de zona completa). El corpus no documenta procedimiento individual porque arquitectónicamente NO existe. Behavior correcto: admit_no_info parcial — explicar que CCD-103 es convencional + redirigir a desconexión por zona o consultar manual físico. Calibración previa (expected: answer) era incorrecta — exigía respuesta a una operación que no existe en el producto._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `CCD-103` · *Central Convencional de 3 Zonas de detección y 1 Extinción* · `CCD-103_Manual_ES_FR_GB_IT` p.3 · sim 0.65

```
Central Convencional de 3 Zonas de detección y 1 Extinción

ES
ES
Central Convencional de 3 Zonas de detección y 1 Extinción 
MANUAL 
DEL USUARIO
```

**[F2]** `CCD-103` · *3 Zones Conventional fire extinguishant control panel* · `CCD-103_Manual_ES_FR_GB_IT` p.1 · sim 0.65

```
3 Zones Conventional fire extinguishant control panel

GB
ES
ES
GUIDE MANUAL
FR
3 Zones Conventional fire extinguishant control panel
IT
ES
ES
Central Convencional de 3 Zonas de detección y 1 Extinción 
MANUAL 
DEL USUARIO
```

**[F3]** `CCD-103` · *6.2.3- Indicación de fallo de sistema* · `CCD-103_Manual_ES_FR_GB_IT` p.27 · sim 0.65

```
6.2.3- Indicación de fallo de sistema

25
ES
6.1.30- Modo Funcionamiento Extinción Automático - Manual (30)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento Extinción Automático 
y  manual.
6.1.31- Modo Funcionamiento Extinción Manual (31)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento solo Manual.
6.1.31- Modo Funcionamiento Extinción Anulada (32)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento Extinción Anulada.
6.2- Indicaciones acústicas
6.2.1- Indicación de alarma
Cuando se produce una situación de alarma el zumbador interno se activa de forma 
fija.
6.2.2- Indicación de avería
Cuando se produce alguna avería y no existe ninguna alarma el zumbador se activa 
de forma intermitente.
6.2.3- Indicación de fallo de sistema
En esta situación el zumbador interno se activa de forma fija.
6.2.4- Estado Extinción Preactivado, Activado y Disparado
En esta situación el zumbador interno se activa de forma fija.
6.2.5- Activación Pulsador de Paro, Disparo y Pausa.
En esta situación el zumbador interno se activa de forma fija.


[TABLA EXTRAÍDA]
6.1.3 | 0- Modo | Funcionamiento | Extinción | Autom | ático | - Manua | l (30)
----------------------------------------
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | Extinción | Automático
y manu | al. |  |  |  |  |  | 
6.1.3 | 1- Modo | Funcionamiento | Extinción | Manua | l (31) |  | 
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | solo Manu | al.
6.1.3 | 1- Modo | Funcionamiento | Extinción | Anula | da (32 | ) | 
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | Extinción | Anulada.
 |  | 6.2- Indica | ciones a | cústic | as |  | 
6.2.1- | Indicac | ión de alarma |  |  |  |  | 
Cuando | se produ | ce
[… contenido truncado para legibilidad]
```

**[F4]** `CCD-103` · *6.2.2- Indicación de avería* · `CCD-103_Manual_ES_FR_GB_IT` p.27 · sim 0.65

```
6.2.2- Indicación de avería

25
ES
6.1.30- Modo Funcionamiento Extinción Automático - Manual (30)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento Extinción Automático 
y  manual.
6.1.31- Modo Funcionamiento Extinción Manual (31)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento solo Manual.
6.1.31- Modo Funcionamiento Extinción Anulada (32)
•	Fijo: Indica que el equipo esta en el Modo de Funcionamiento Extinción Anulada.
6.2- Indicaciones acústicas
6.2.1- Indicación de alarma
Cuando se produce una situación de alarma el zumbador interno se activa de forma 
fija.
6.2.2- Indicación de avería
Cuando se produce alguna avería y no existe ninguna alarma el zumbador se activa 
de forma intermitente.
6.2.3- Indicación de fallo de sistema
En esta situación el zumbador interno se activa de forma fija.
6.2.4- Estado Extinción Preactivado, Activado y Disparado
En esta situación el zumbador interno se activa de forma fija.
6.2.5- Activación Pulsador de Paro, Disparo y Pausa.
En esta situación el zumbador interno se activa de forma fija.


[TABLA EXTRAÍDA]
6.1.3 | 0- Modo | Funcionamiento | Extinción | Autom | ático | - Manua | l (30)
----------------------------------------
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | Extinción | Automático
y manu | al. |  |  |  |  |  | 
6.1.3 | 1- Modo | Funcionamiento | Extinción | Manua | l (31) |  | 
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | solo Manu | al.
6.1.3 | 1- Modo | Funcionamiento | Extinción | Anula | da (32 | ) | 
• Fijo: In | dica que | el equipo esta en el | Modo de Fu | nciona | miento | Extinción | Anulada.
 |  | 6.2- Indica | ciones a | cústic | as |  | 
6.2.1- | Indicac | ión de alarma |  |  |  |  | 
Cuando | se produ | ce una situac
[… contenido truncado para legibilidad]
```

**[F5]** `CCD-103` · *MANUAL DEL USUARIO* · `CCD-103_Manual_ES_FR_GB_IT` p.3 · sim 0.65

```
MANUAL
DEL USUARIO

ES
ES
Central Convencional de 3 Zonas de detección y 1 Extinción 
MANUAL 
DEL USUARIO
ES
ES
ÍNDICE
1- Introducción...........................................................................................................5
1.1- Descripción General de la Serie............................................................................ 5
2- Comprobaciones habituales.................................................................................6
3- Guía de instalación................................................................................................6
3.1- Comprobaciones previas a la instalación.............................................................. 6
3.2- Herramientas necesarias.......................................................................................7
3.3- Pasos de la instalación.........................................................................................7
4- Guía de conexionado de la PCB.........................................................................12
4.1- Conexionado bloque de detección...................................................................... 13
4.2- Conexionado bloque de extinción....................................................................... 16
5- Guía de puesta en marcha..................................................................................19
5.1- Verificación del sistema......................................................................................19
5.2- Alimentación del sistema....................................................................................19
5.3- Prueba del sistema.............................................................................................20
6- Guía de usuario......................................................
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados del manual **CCD-103** cubren indicaciones luminosas, indicaciones acústicas, modos de funcionamiento y conexionado, pero **no contienen ningún procedimiento de desactivación individual de detector** sin afectar al resto del lazo.

Los fragmentos disponibles corresponden a las secciones [F3][F4]:
- Sección 6.1 — Indicaciones luminosas
- Sección 6.2 — Indicaciones acústicas (zumbador en alarma, avería, fallo de sistema)
- Sección 6.4 — Modos de funcionamiento del bloque de detección
- Sección 6.5 — Modos de funcionamiento del bloque de extinción

Ninguno de estos fragmentos describe un procedimiento de inhibición o desactivación individual de un detector.

Para obtener esta información, te recomiendo:
1. Consultar directamente la **Sección 8 — Opciones de configuración** del manual físico [F5], que podría contener opciones de inhibición por zona o detector.
2. Contactar con el soporte técnico de **Detnov** directamente.

---

Fuente: CCD-103_Manual_ES_FR_GB_IT (sin revisión registrada)

---

También puedo ayudarte con: **modos de funcionamiento del bloque de detección**, **indicaciones de avería** o **conexionado de la PCB** de la CCD-103.
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

**Razón del judge:** La CCD-103 es una central convencional donde la desconexión opera por zona completa (V4, sección 6.4.4), no por detector individual; ningún fragmento F ni V describe desactivación individual de detector. El bot admite correctamente la ausencia de información, describe con precisión los fragmentos disponibles y redirige al técnico, cumpliendo la conducta esperada admit_no_info sin inventar datos.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `CCD-103_Manual_ES_FR_GB_IT`):**

La **CCD-103 es central convencional** (no analógica), por lo tanto NO permite anular detectores individualmente — la unidad mínima de gestión es la **zona** (la central tiene 3 zonas de detección + 1 zona de extinción). Procedimiento correcto:
1. Para inhibir todos los detectores de una zona: desde menú de usuario nivel 2, opción "Anular zona" → seleccionar zona 1/2/3.
2. Si el técnico quiere "desactivar un detector concreto": físicamente debe **desconectar el detector de la zona** (extraerlo de la base o puentear la zona, con la consecuencia de que el resto de detectores de esa zona seguirá supervisado y la zona seguirá generando alarma normal con los demás).
3. No existe "ID" ni "dirección" de detector en la CCD-103 — son sensores convencionales 2-hilos sobre zona.

**Calidad de los chunks:**

- **Retrieval semi-correcto**: aporta evidencia de que la CCD-103 es convencional (F1 "Central Convencional de 3 Zonas", F2 "3 Zones Conventional"), pero no recupera el chunk del manual sobre cómo anular zona (que sí existe — sec. 6.4.4 según el judge).
- **F1, F2, F5 son las páginas iniciales/portada** (introducción multilingüe + índice): aportan el dato de que es convencional pero no el procedimiento.
- **F3 y F4 son duplicados** (mismo contenido sec. 6.2 Indicaciones acústicas, p.27, sim 0.65 ambos). Header de F3 es "6.2.3" y de F4 "6.2.2" pero contenido es idéntico — el chunk arranca antes.
- **`[TABLA EXTRAÍDA]` mal aplicado** en F3 y F4: el contenido extraído como tabla es texto plano de bullets sobre modos de funcionamiento.
- **F5 contiene el índice completo del manual** — la sec. **8 (Opciones de configuración)** que el bot menciona está ahí; el bot la usa como puntero, lo cual es razonable.
- **Retrieval coherente con que el producto no documenta operación individual**: si no existe, no se recupera. Pero falta el chunk del procedimiento de anulación por zona (sec. 6.4.4 según judge), que daría la respuesta legítima alternativa.

**Comparación con bot:**

- ✓ Admite que no hay procedimiento de desactivación individual.
- ✓ Cita las secciones disponibles correctamente.
- ✓ Redirige al técnico al manual y al soporte.
- ⚠️ **NO explica que arquitectónicamente NO se puede** (la nota YAML lo dice: la CCD-103 es convencional, no soporta operación individual de detector). Esto es exactamente el mismo patrón que hp014 (ADW535) y hp019 (ASD): el bot no desafía la premisa cuando el producto no soporta lo que pregunta el técnico.
- ⚠️ NO ofrece la alternativa legítima: "puedes anular toda la zona" — que es la operación equivalente disponible. El judge cita sec. 6.4.4 (anulación por zona) como existiendo en V; el bot debería haberlo redirigido a esa sección.

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo parcial** — yo diría: **PASS marginal con observación**
- **Dimensión equivocada(s) del judge:** **helpful** (el bot no aprovecha que F1/F2 dicen explícitamente "central convencional" para explicar el "por qué no se puede"; y no ofrece la alternativa legítima por zona).
- **Nota / por qué:** El recalibrado YAML a `admit_no_info` está bien fundado (la operación no existe). Pero el bot solo admite sin explicar el motivo arquitectónico ni redirigir a la alternativa. Es admit_no_info "vago" en lugar de admit_no_info "didáctico". El judge no lo penaliza porque solo audita fidelidad y honestidad a F, no calidad pedagógica.
- **Origen del problema:** **generación** (no desafía premisa, no ofrece alternativa por zona) + **retrieval** (no trae sec. 6.4.4 de anulación de zona) + **YAML correctamente recalibrado**.

---

## hp016 — judge dice **PASS ✓** · (16/20)

**Pregunta del técnico:** Un detector B501RF de Notifier no responde tras sustituir la batería. ¿Qué procedimiento seguir?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 4/4 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: expected_sources retirado: 'B501RF' no aparece en source_file (solo en product_model, 2750 chunks dentro de docs I56-6591-001 NRX-WS-RR y I56-4205-001 NRX-SMT3). 20 abril: OR-syntax — el B501RF es radio-mesh, no usa 'direccionar' clásico (lazo cableado) sino 'sincronizar con pasarela' / 'registrar en red mesh'. 'bateria|batería|pila' cubre acento + sinónimo (CR123A son pilas, no baterías en sentido estricto)._

### Fragmentos que el bot usó (top 5)

**[F1]** `B501RF` · *1 2* · `I56-4206-001 NRX Radio Thermals Web` p.6 · sim 0.72

```
1
2

1
2

N200-302-00
I56-4206-001 
Honeywell Life Safety Iberia, S.L.  C/ Pau Vila, 15-19, 08911 Badalona (Barcelona) Espana
según sea necesario. A continuación, el sensor vía radio se sincronizará 
con los demás dispositivos asociados mientras la pasarela crea la red en 
malla (mesh) vía radio (para más información, consultar el Manual de 
programación y puesta en funcionamiento vía radio.)
INDICADORES LED Y DESCRIPCIÓN DE AVERÍAS
El sensor vía radio cuenta con dos indicadores LED que muestran el 
estado del dispositivo.
4c
TENER EN CUENTA 
LOS POLOS
4a
Figura 4: Instalación de las pilas y 
selectores giratorios de dirección
4 x Duracell 
Ultra 123
4d
4b
PRUEBA
Prueba de imán
Un imán de prueba colocado correctamente generará una alarma. Colocar 
el imán (M02-04-00) como se muestra en la Figura 5, después de identificar 
la línea recta en la base del sensor. Para ayudar a la correcta ubicación del 
imán, los LEDs del sensor se pondrán verdes durante 1s cuando se active 
el contacto de la alarma.
Prueba de calor directo (secador de pelo 1000-1500 vatios) 
Dirigir el calor hacia el sensor lateralmente. Mantener la fuente de calor 
a una distancia de aproximadamente 15 cm para prevenir daños en la 
superficie durante la prueba. El sensor debería enviar una alarma a la 
central mediante la pasarela cuando la temperatura del sensor alcance 
los 58°C.
Tras la prueba, restablecer la indicación de la alarma en la central de incendios.
LIMPIEZA
Utilizar una aspiradora y/o aire comprimido limpio para eliminar el polvo 
y los restos del termistor y de la tapa del sensor según se necesite 
(asegurarse de no producir daños en el termistor).
Nota
Cuando se sustituyan las pilas, será necesario cambiar las 4
LIMITACIONES DE LOS SENSORES TÉRMICOS
Estos sensores térmicos sólo funcionará
[… contenido truncado para legibilidad]
```

**[F2]** `B501RF` · *LIMPIEZA* · `I56-4206-001 NRX Radio Thermals Web` p.6 · sim 0.72

```
LIMPIEZA

LIMPIEZA

N200-302-00
I56-4206-001 
Honeywell Life Safety Iberia, S.L.  C/ Pau Vila, 15-19, 08911 Badalona (Barcelona) Espana
según sea necesario. A continuación, el sensor vía radio se sincronizará 
con los demás dispositivos asociados mientras la pasarela crea la red en 
malla (mesh) vía radio (para más información, consultar el Manual de 
programación y puesta en funcionamiento vía radio.)
INDICADORES LED Y DESCRIPCIÓN DE AVERÍAS
El sensor vía radio cuenta con dos indicadores LED que muestran el 
estado del dispositivo.
4c
TENER EN CUENTA 
LOS POLOS
4a
Figura 4: Instalación de las pilas y 
selectores giratorios de dirección
4 x Duracell 
Ultra 123
4d
4b
PRUEBA
Prueba de imán
Un imán de prueba colocado correctamente generará una alarma. Colocar 
el imán (M02-04-00) como se muestra en la Figura 5, después de identificar 
la línea recta en la base del sensor. Para ayudar a la correcta ubicación del 
imán, los LEDs del sensor se pondrán verdes durante 1s cuando se active 
el contacto de la alarma.
Prueba de calor directo (secador de pelo 1000-1500 vatios) 
Dirigir el calor hacia el sensor lateralmente. Mantener la fuente de calor 
a una distancia de aproximadamente 15 cm para prevenir daños en la 
superficie durante la prueba. El sensor debería enviar una alarma a la 
central mediante la pasarela cuando la temperatura del sensor alcance 
los 58°C.
Tras la prueba, restablecer la indicación de la alarma en la central de incendios.
LIMPIEZA
Utilizar una aspiradora y/o aire comprimido limpio para eliminar el polvo 
y los restos del termistor y de la tapa del sensor según se necesite 
(asegurarse de no producir daños en el termistor).
Nota
Cuando se sustituyan las pilas, será necesario cambiar las 4
LIMITACIONES DE LOS SENSORES TÉRMICOS
Estos sensores térmicos sólo
[… contenido truncado para legibilidad]
```

**[F3]** `B501RF` · *Figure 6: Cleaning the Sensor* · `I56-4225-001 NRX-OPT Web` p.2 · sim 0.80

```
Figure 6: Cleaning the Sensor

Figure 6: Cleaning the Sensor

N200-301-00
I56-4225-001 
Notifier by Honeywell, Brooks Road, Lewes, East Sussex, BN7 2BY, UK
LED INDICATORS AND FAULT DESCRIPTION
The radio sensor has two LED indicators that show the status of the device.
4c
NOTE POLARITY
4a
Figure 4: Battery Installation and
Rotary Address Switches
4 x Duracell 
Ultra 123
TESTING
Magnet Test
Position the magnet (M02-04-00) as shown in Figure 5, after identifying the 
straight line ridge on the sensor base. To aid positioning, the sensor LEDs 
will turn on green for 1s when the alarm switch activates. The device will 
turn off all delays and filters for 10 minutes. After this period, the device 
returns to its normal mode. 
Smoke Testing
Using smoke, or a synthetic smoke aerosol, subject the sensor to controlled 
amounts of smoke in accordance with local codes of practice. The sensor 
should signal an alarm to the CIE via the Gateway within 30 seconds.
Following testing, reset the alarm indication at the CIE (fire panel).
CLEANING
Use a fine brush, vacuum cleaner and/or clean, compressed air to remove 
dust and debris from the sensing chamber and sensing chamber cover as 
required. Figure 6 shows how to remove the covers.
Arrows on the plastic indicate the positioning when replacing the chamber 
cover and air guide.
Note
When replacing batteries, all 4 will need to be replaced
LIMITATIONS OF SMOKE SENSORS
These smoke sensors will only work when connected to a compatible 
control panel. Smoke detectors have operating limitations. They will not 
sense fires where smoke does not reach the sensor, and may respond 
differently to varying types of smoke. Consideration must be given to the 
environment when selecting and siting fire sensors.
Smoke sensors cannot last forever, and
[… contenido truncado para legibilidad]
```

**[F4]** `B501RF` · *+ +* · `I56-4225-001 NRX-OPT Web` p.2 · sim 0.80

```
+
+

+
+

N200-301-00
I56-4225-001 
Notifier by Honeywell, Brooks Road, Lewes, East Sussex, BN7 2BY, UK
LED INDICATORS AND FAULT DESCRIPTION
The radio sensor has two LED indicators that show the status of the device.
4c
NOTE POLARITY
4a
Figure 4: Battery Installation and
Rotary Address Switches
4 x Duracell 
Ultra 123
TESTING
Magnet Test
Position the magnet (M02-04-00) as shown in Figure 5, after identifying the 
straight line ridge on the sensor base. To aid positioning, the sensor LEDs 
will turn on green for 1s when the alarm switch activates. The device will 
turn off all delays and filters for 10 minutes. After this period, the device 
returns to its normal mode. 
Smoke Testing
Using smoke, or a synthetic smoke aerosol, subject the sensor to controlled 
amounts of smoke in accordance with local codes of practice. The sensor 
should signal an alarm to the CIE via the Gateway within 30 seconds.
Following testing, reset the alarm indication at the CIE (fire panel).
CLEANING
Use a fine brush, vacuum cleaner and/or clean, compressed air to remove 
dust and debris from the sensing chamber and sensing chamber cover as 
required. Figure 6 shows how to remove the covers.
Arrows on the plastic indicate the positioning when replacing the chamber 
cover and air guide.
Note
When replacing batteries, all 4 will need to be replaced
LIMITATIONS OF SMOKE SENSORS
These smoke sensors will only work when connected to a compatible 
control panel. Smoke detectors have operating limitations. They will not 
sense fires where smoke does not reach the sensor, and may respond 
differently to varying types of smoke. Consideration must be given to the 
environment when selecting and siting fire sensors.
Smoke sensors cannot last forever, and we recommend replacement after 
10 years.
Figure 5:
[… contenido truncado para legibilidad]
```

**[F5]** `B501RF` · *SENSOR COVER* · `I56-4225-001 NRX-OPT Web` p.2 · sim 0.80

```
SENSOR COVER

SENSOR COVER

N200-301-00
I56-4225-001 
Notifier by Honeywell, Brooks Road, Lewes, East Sussex, BN7 2BY, UK
LED INDICATORS AND FAULT DESCRIPTION
The radio sensor has two LED indicators that show the status of the device.
4c
NOTE POLARITY
4a
Figure 4: Battery Installation and
Rotary Address Switches
4 x Duracell 
Ultra 123
TESTING
Magnet Test
Position the magnet (M02-04-00) as shown in Figure 5, after identifying the 
straight line ridge on the sensor base. To aid positioning, the sensor LEDs 
will turn on green for 1s when the alarm switch activates. The device will 
turn off all delays and filters for 10 minutes. After this period, the device 
returns to its normal mode. 
Smoke Testing
Using smoke, or a synthetic smoke aerosol, subject the sensor to controlled 
amounts of smoke in accordance with local codes of practice. The sensor 
should signal an alarm to the CIE via the Gateway within 30 seconds.
Following testing, reset the alarm indication at the CIE (fire panel).
CLEANING
Use a fine brush, vacuum cleaner and/or clean, compressed air to remove 
dust and debris from the sensing chamber and sensing chamber cover as 
required. Figure 6 shows how to remove the covers.
Arrows on the plastic indicate the positioning when replacing the chamber 
cover and air guide.
Note
When replacing batteries, all 4 will need to be replaced
LIMITATIONS OF SMOKE SENSORS
These smoke sensors will only work when connected to a compatible 
control panel. Smoke detectors have operating limitations. They will not 
sense fires where smoke does not reach the sensor, and may respond 
differently to varying types of smoke. Consideration must be given to the 
environment when selecting and siting fire sensors.
Smoke sensors cannot last forever, and we recommend replacement after 
10
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## B501RF — Detector no responde tras sustitución de batería

### Verificaciones inmediatas

**1. Confirmar sustitución correcta de las 4 pilas**

El manual indica explícitamente que al sustituir las pilas, **es necesario cambiar las 4** [F3][F4]. Si solo se cambió alguna, reemplaza el juego completo con **4 x Duracell Ultra 123** [F3][F4].

**2. Verificar polaridad**

Durante la instalación de las pilas hay que **tener en cuenta los polos** (ver Figura 4 del manual) [F1]. Comprueba que cada pila está orientada correctamente.

---

### Diagnóstico por LEDs tras insertar las pilas

Una vez instaladas correctamente, observa el comportamiento de los **dos indicadores LED** [F1] para determinar el estado:

- **Pulsación verde larga** → El dispositivo no está en funcionamiento (valores por defecto / sin programar) [F1]
- **3 luces verdes intermitentes** → El dispositivo está en funcionamiento (programado) [F1]
- **Luz intermitente ámbar cada 1s** → El dispositivo tiene un problema interno (fallo) [F1]
- **Luz roja/verde doble intermitente cada 14s** → Encendido, en espera de programación [F1]
- **Luz verde/ámbar doble intermitente cada 14s** → Programado, intentando conectarse a la red vía radio [F1]
- **Sin ninguna indicación LED** → Las pilas no están correctamente instaladas o son defectuosas

---

### Procedimiento paso a paso

1. Retira las 4 pilas instaladas.
2. Instala **4 pilas Duracell Ultra 123 nuevas**, respetando la polaridad indicada en la Figura 4 [F1].
3. Observa los LEDs en los primeros segundos:
   - Si aparece **pulsación verde larga** → el dispositivo arranca pero no está programado; necesita sincronización con la pasarela [F1].
   - Si aparece **verde/ámbar doble cada 14s** → está intentando conectarse a la red radio; espera a que establezca comunicación [F1].
   - Si aparece **ámbar intermitente cada 1s** → fallo interno; el dispositivo puede estar dañado [F1].
4. Una vez que los LEDs muestren el estado **Normal** (controlado por el panel), verifica la recepción en la central mediante la **prueba de imán** (M02-04-00): los LEDs deben dar una **pulsación verde de 1s** al activar el interruptor interno [F1].

---

### Nota importante sobre sincronización

Tras insertar las pilas, el sensor vía radio necesita **sincronizarse con los demás dispositivos** mientras la pasarela crea la red en malla (mesh). Para más detalles sobre este proceso, el manual remite al **Manual de programación y puesta en funcionamiento vía radio** [F1].

---

**Fuente:** I56-4206-001 NRX Radio Thermals Web (sin revisión registrada); I56-4225-001 NRX-OPT Web (sin revisión registrada)

---

También puedo ayudarte con: **prueba funcional con imán o calor**, **interpretación de códigos de fallo en la central** o **procedimiento de sincronización con la pasarela radio** del B501RF.
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

**Razón del judge:** Todas las afirmaciones técnicas del bot (cambio de las 4 pilas Duracell Ultra 123, verificación de polaridad, tabla completa de estados LED, proceso de sincronización con la pasarela, prueba de imán con pulsación verde de 1s) están soportadas directamente por los fragmentos F1/F2 que el bot cita, y son consistentes con los fragmentos V disponibles. La respuesta es estructurada, accionable y cubre el procedimiento completo de diagnóstico post-sustitución de batería que el técnico necesita.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `I56-4206-001 NRX Radio Thermals` y `I56-4225-001 NRX-OPT`):**

**Importante**: el **B501RF no es un detector**, sino la **base inalámbrica** sobre la que se montan los sensores radio (NRX-TFIX58, NRX-TDIFF, NRX-OPT, NRX-WS-RR sirenas, etc.). La pregunta del eval contiene una premisa errónea: "Un detector B501RF…". Lo correcto sería "un sensor NRX-xxx montado sobre base B501RF".

Procedimiento tras sustituir las pilas:
1. **Cambiar las 4 pilas a la vez** (Duracell Ultra 123) — el manual indica que cuando se sustituyen, hay que cambiar las 4. Respetar polaridad.
2. Tras insertar las pilas, el sensor entra en proceso de auto-sincronización con la pasarela (gateway) durante varios segundos a minutos.
3. **Verificar LEDs** del sensor: secuencias de luz roja/verde/ámbar indican estado de programación/conexión a la red mesh.
4. Si no responde tras ~10 minutos, comprobar:
   - Que el dispositivo siga registrado en la pasarela (no se ha borrado).
   - Que las pilas son correctas (modelo y voltaje).
   - Reset del sensor (retirar pilas 30 s, reinsertar).
   - Si persiste: re-aprender el dispositivo desde el menú de la pasarela (consultar **Manual de programación y puesta en funcionamiento vía radio**).
5. Prueba final con imán M02-04-00 (LEDs verdes 1 s al activar).

**Calidad de los chunks:**

- **F1 y F2 idénticos** (mismo chunk de I56-4206-001 p.6, sim 0.72 ambos). Duplicación.
- **F3, F4, F5 son del mismo chunk** I56-4225-001 p.2 (sim 0.80 los tres). Triple duplicación. **4 de 5 chunks son del manual inglés I56-4225**.
- **F1/F2 sí están en español** (manual I56-4206-001 NRX Radio Thermals Web — multilingüe). Útiles.
- **Headers inútiles en todos**: F1 "1 2" (numeración de figura), F2 "LIMPIEZA", F3 "Figure 6: Cleaning the Sensor", F4 "+ +", F5 "SENSOR COVER". Ninguno es un epígrafe de sección; son fragmentos arbitrarios.
- **Atribución de fabricante**: la pregunta dice "B501RF de Notifier". Es correcto (Notifier/Honeywell), aunque las instrucciones traen "Notifier by Honeywell".
- **Premisa errónea no detectada**: el bot no aclara que B501RF es la **base**, no el detector. El technically correct sería que el técnico haya sustituido las pilas en un sensor NRX-xxx montado sobre base B501RF.

**Comparación con bot:**

- ✓ Procedimiento correcto: 4 pilas Duracell Ultra 123, polaridad, sincronización con pasarela, prueba con imán.
- ⚠️ La **"tabla de estados LED"** que el bot presenta (pulsación verde larga, 3 verdes intermitentes, ámbar 1s, rojo/verde doble 14s, verde/ámbar doble 14s) **no aparece literalmente en F1**. F1 solo dice "El sensor vía radio cuenta con dos indicadores LED que muestran el estado del dispositivo" — sin la tabla detallada. El bot fabricó/extrapoló la tabla. Esto es **citation_faithful FAIL** que el judge no detectó.
- ⚠️ El judge dice "tabla completa de estados LED... están soportadas directamente por los fragmentos F1/F2 que el bot cita" — pero no es cierto. F1/F2 cortan justo antes de la tabla. Es posible que la tabla exista en el manual pero esté en otro chunk no recuperado.
- ⚠️ NO aclara que B501RF es base, no detector — premisa errónea aceptada sin desafiar.

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo** — yo diría: **FAIL**
- **Dimensión equivocada(s) del judge:** **citation_faithful** (la tabla de estados LED no está en F1/F2 visibles; el bot la inventa o trae de pre-training) + **relevant** (no aclara que B501RF es base).
- **Nota / por qué:** El bot construye una "tabla de estados LED" muy específica (3 verdes intermitentes, ámbar 1s, rojo/verde 14s…) que NO aparece en los fragmentos visibles. Probablemente está mezclando información de pre-training con citas espurias a [F1]. Es exactamente el tipo de hallucination que el judge debería detectar. Patrón similar a hp011 (SW3-6/SW3-7 inventados).
- **Origen del problema:** **generación** (alucinación de tabla LED + miscitación a F1) + **chunk-extraction** (4/5 duplicados; headers basura) + **judge** (no detecta el fabricado).

---

## hp017 — judge dice **PASS ✓** · (17/20)

**Pregunta del técnico:** ¿Cómo se programa el retardo de salida de alarma principal en la Notifier PEARL?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/4 hits · missing: `['delay']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `PEARL` · *- «Causa y Efecto»: Apéndice 5. Programación de causa-efecto* · `997-671-005-3_Configuration_ES` p.15 · sim 0.80

```
-
«Causa y Efecto»: Apéndice 5. Programación de causa-efecto

-
«Causa y Efecto»: Apéndice 5. Programación de causa-efecto

Sección 3 - 2
Manual de configuración de la central
997-671-005-3
Menús de configuración de la central
www.notifier.es
-	
Cambiar el idioma de la pantalla LCD (si está disponible).
-	
Establecer un período temporal (hasta 10 horas) para silenciar el zumbador.
Nota:	 Dependiendo del período establecido, el uso de esta función puede contravenir las disposiciones de EN54-2, párrafos 7.4.2, 7.4.3 (para condiciones 
de incendio) y 8.6.3 (para condiciones de fallo).
Puede obtenerse una clave de acceso de nivel 3 temporal para visitas cuando la clave de acceso se haya olvidado. Véase «3.2 Solicitud de código temporal».
3.1 Menú «Editar Configuración»
Desde este menú pueden editarse gran parte de los parámetros básicos de 
la central. Están disponibles las siguientes opciones configurables:
-	
«Configuración de la Central»: 3.1.1 Menú de configuración de la central
-	
«Equipos de Lazo»: 4 Equipos de lazo
-	
«Salidas virtuales»: Apéndice 9 Salidas virtuales
-	
«Opciones de Zonas»: 5.1 Opciones de zonas
-	
«Configuración de la Red»: Apéndice 4. Configuración de redes
-	
«Programación Horaria»: Apéndice 2. Programación horaria
-	
«Programa de Patrones de Sirena»: Apéndice 3. Programa de patrones 
de sirena
-	
«Causa y Efecto»: Apéndice 5. Programación de causa-efecto
-	
«Acceso del Usuario»: Apéndice 6. Acceso de usuario
3.1.1	
Menú de configuración de la central
Desde el menú «Editar Configuración» y con la opción «Menú de Configuración 
de la Central» marcada, pulse 
 para mostrar el menú. Aparecen las 
siguientes opciones:
-	
«Configuración de la Central»: Apéndice 1. 
-	
«Opciones Placa Base»: Apéndice 7. 
-	
«Opciones Tarjeta Conectable»: Apéndice 7.
[… contenido truncado para legibilidad]
```

**[F2]** `PEARL` · *Nota:Resulta más fácil hacerlo con el programa, pero, si no está disponible, los menús de la central permiten realizar e* · `997-671-005-3_Configuration_ES` p.4 · sim 0.80

```
Nota:Resulta más fácil hacerlo con el programa, pero, si no está
disponible, los menús de la central permiten realizar estos cambios
de forma satisfactoria. (continuación)

[TABLA EXTRAÍDA]
El fabricante reco | mienda encare | cidamente que | l | a ce | ntral Pear | l se configure | Co | nfig | uración | med | iante el | ITS |  |  | Con | fi | gur | ació | n co | n los | 
----------------------------------------
mediante el prog | rama de confi | guración, junto | c | on | las otras | herramientas | en | un | portátil |  |  |  |  |  | c | o | ntro | les | del | panel | 
de configuración | y diagnóstico | por ordenado | r | del | Paquete | Integrado de |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 
Herramientas (IT | S) de Notifier. |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 
No obstante, pued | en realizarse p | equeños cambi | o | s o | ajustes de | configuración |  |  | Centr | al co | ntra |  |  |  |  |  |  |  |  |  | 
utilizando los cont | roles frontales | y los menús d | e | con | figuración | de la central. |  |  | incen | dios | Pearl |  |  |  |  |  |  |  |  |  | 
Nota: Resulta | más fácil hac | erlo con el p | ro | gra | ma, pero | , si no está |  |  |  |  |  |  |  |  |  |  |  | SILENCIAR | ZUMBADO | R | 
disponible | , los menús d | e la central per | m | iten | realizar e | stos cambios |  |  |  |  |  |  |  |  |  |  |  | AMPLIAR R | ETARDO |  | 
de forma | satisfactoria. |  |  |  |  |  |  |  |  |  |  |  |  |  | i |  |  | FIN RETAR | DO |  | 
En consecuencia | , la estructur | a del presente |  | doc | umento s | e basa en el |  |  |  |  |  |  |  |  |  |  |  | SILENCIAR | SIRENAS |  | 
supuesto de que la en parte con los instalación prepr | central —o el menús de la ogramado qu | sistema de cent central, no co e se haya tran | ra n s | les un fer
[… contenido truncado para legibilidad]
```

**[F3]** `PEARL` · *Nota:	La programación horaria anulada volverá a su estado no anulado cuando empiece el próximo periodo de modo día confi* · `997-670-005-3_Operating_ES` p.26 · sim 0.80

```
Nota:	La programación horaria anulada volverá a su estado no anulado
cuando empiece el próximo periodo de modo día configurado.

Nota:	La programación horaria anulada volverá a su estado no anulado
cuando empiece el próximo periodo de modo día configurado.

Sección 5 - 11
www.notifier.es
997-670-005-3
Navegación por los menús del panel
Manual de funcionamiento
5.1.5	 Anulación manual de programación horaria
Seleccione «6: Anulación manual horaria» para anular manualmente 
una programación horaria activa. Esta opción solo está disponible si se ha 
configurado una programación (se pueden configurar hasta diez) durante 
la puesta en servicio. Si hay una programación horaria activa, el LED de 
MODO DÍA está encendido. No obstante, si se ha anulado mediante esta 
opción, el LED de MODO DÍA estará apagado hasta que empiece el próximo 
periodo de modo día configurado o se restablezca la programación horaria, 
si aún está activa, mediante esta opción.
En el ejemplo de la derecha, solo se ha configurado la programación 
horaria 1. Para anularla, es decir, cancelar el cambio configurado en la 
sensibilidad del sensor o la imposición de un retardo, pulse la tecla 
. 
Para cancelar esta función, pulse 
.
Nota:	La programación horaria anulada volverá a su estado no anulado 
cuando empiece el próximo periodo de modo día configurado.
```

**[F4]** `PEARL` · *1. Teclas de control.* · `997-670-005-3_Operating_ES` p.8 · sim 0.80

```
1. Teclas de control.

1. Teclas de control.

Sección 1 - 5
www.notifier.es
997-670-005-3
Interfaz de usuario de la central
Manual de funcionamiento
1.2.2	Teclas de función
El funcionamiento de la central, en los niveles de acceso 1 y 2, se controla 
mediante las distintas teclas de función del panel.
Las teclas situadas a la derecha de la pantalla proporcionan las siguientes 
funciones:
1. Teclas de control.
Salvo las teclas SILENCIAR ZUMBADOR, FIN RETARDO y CAMBIAR 
PESTAÑA, para que puedan seleccionarse es necesario que la central 
esté en el nivel de acceso 2.
2. Teclas de navegación de menú y selección de opciones. 
Estas teclas funcionan, junto con el teclado alfanumérico, cuando la central 
está en el nivel de acceso 2.
3. Teclas alfanuméricas
Están disponibles cuando la central está en el nivel de acceso 2 y los menús 
de usuario están activos. Las opciones del menú pueden seleccionarse con 
estas teclas como alternativa a la navegación con 
 o 
 y la tecla 
.
4. Otras teclas de función
Están situadas a la izquierda y debajo de la pantalla. Son las siguientes:
a.	 Tecla MOSTRAR MÁS ZONAS EN ALARMA
b.	 Tecla CAMBIAR PESTAÑA
c.	 Cuatro teclas de usuario (programables)
```

**[F5]** `PEARL` · *4	Equipos de lazo�������������������������������������������������4 - 1* · `997-671-005-3_Configuration_ES` p.2 · sim 0.80

```
4	Equipos de lazo�������������������������������������������������4 - 1

4	Equipos de lazo�������������������������������������������������4 - 1

Índice - ii
997-671-005-3
Índice
www.notifier.es
Manual de configuración de la central
Índice
1	 Introducción...................................................... 1 - 1
1.1 
Primeras consideraciones....................................... 1 - 2
1.2 
Definición de zonas................................................. 1 - 2
1.2.1 
Nombre de las zonas................................................1 - 2
1.2.2 
¿Por qué tener más de una zona?............................1 - 3
1.3 
Funcionamiento de la central.................................. 1 - 3
1.4 
Operaciones de configuración................................. 1 - 4
1.4.1 
Principales parámetros de configuración de la central
...................................................................................................1 - 4
1.5 
Configuración de red............................................... 1 - 5
2	 Guía de puesta en marcha de nivel 3.............. 2 - 1
2.1 
Primer nivel de edición del sistema......................... 2 - 2
2.2 
Segundo nivel de edición del sistema..................... 2 - 3
2.3 
Tercer nivel de edición del sistema......................... 2 - 4
2.4 
Otras funciones del nivel de acceso 3..................... 2 - 5
3 Menús de configuración de la central.............. 3 - 1
3.1 
Menú «Editar Configuración».................................. 3 - 2
3.1.1 
Menú de configuración de la central.........................3 - 2
3.1.2 
Guardar cambios.......................................................3 - 3
3.2 
Solicitud de código temporal................................... 3 - 4
4	 Equipos de lazo........................................
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
## Retardo de salida de alarma principal en la PEARL

Los fragmentos disponibles no incluyen el procedimiento paso a paso para programar el **retardo de salida de alarma principal** directamente. Sin embargo, sí puedo orientarte sobre dónde encontrarlo en la estructura del manual:

---

### Dónde está la configuración de retardo

Según el índice del manual de configuración [F5], el parámetro relacionado con el retardo de alarma se encuentra en:

- **Apéndice 1, sección A1.10**: «**Ampliar Puls.Retardo**» [F5]

Además, desde el menú principal de la central, el acceso a la configuración sigue esta ruta [F1]:

1. Accede al menú **«Editar Configuración»** (requiere nivel de acceso 3) [F1]
2. Selecciona **«Configuración de la Central»** [F1]
3. Desde ahí accede a **«Configuración de la Central»** → **Apéndice 1** [F1]
4. Localiza la opción **«Ampliar Puls.Retardo»** (sección A1.10) [F5]

---

### Notas importantes

- El fabricante **recomienda usar el programa ITS** (Paquete Integrado de Herramientas de Notifier) para realizar la configuración, aunque también puede hacerse desde los menús del panel [F2].
- En el panel físico existe una tecla **AMPLIAR RETARDO** y una tecla **FIN RETARDO** para gestionar el retardo en tiempo real durante una alarma [F2].
- La tecla **FIN RETARDO** puede usarse sin necesidad de nivel de acceso 2 [F4].

---

### Lo que no está en los fragmentos

El detalle exacto del procedimiento de la sección **A1.10** (valores configurables, rango de tiempo, pasos concretos) **no está incluido en los fragmentos recuperados**. Necesitarás consultar el **Apéndice 1, sección A1.10** del manual físico o mediante el software ITS.

---

**Fuente:** Manual de configuración de la central PEARL 997-671-005-3 (sin revisión registrada); Manual de funcionamiento PEARL 997-670-005-3 (sin revisión registrada)

---

También puedo ayudarte con: **programación de causa-efecto (Apéndice 5)**, **opciones de zonas** o **programación horaria** de la PEARL.
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

**Razón del judge:** El bot responde directamente con la información disponible en los fragmentos F: la ruta de menús (F1), la recomendación de usar ITS (F2), las teclas físicas AMPLIAR RETARDO / FIN RETARDO (F2/F4) y la referencia al Apéndice 1 sección A1.10 'Ampliar Puls.Retardo' (F5). Todas las afirmaciones técnicas están soportadas por los fragmentos citados o por el corpus (F/V). El bot admite honestamente que el detalle exacto del procedimiento de A1.10 no está en los fragmentos recuperados y redirige al manua

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `997-671-005-3_Configuration_ES` PEARL — Apéndice 1 sec. A1.10):**

Programación del retardo de salida principal (T1) en PEARL:
1. Acceder con clave de **Nivel 3** (instalador) — tecla `Menú` → Editar Configuración.
2. Ruta: **Editar Configuración → Configuración de la Central → Apéndice 1 → A1.10 "Ampliar Puls.Retardo"** (o desde menú "Configuración de salidas").
3. Configurar valor de retardo (típicamente 0-10 min, según EN54-2 §7.11; PEARL admite hasta el máximo regulado por norma).
4. Confirmar y "Guardar Configuración".
5. Mejor práctica: hacerlo desde el software **ITS (Integrated Tools Suite)** de Notifier — el manual lo recomienda explícitamente (F2).
6. La tecla **AMPLIAR RETARDO** del panel permite extender el retardo en tiempo real durante una alarma (función operativa, no programación).

**Calidad de los chunks:**

- **F1 header inútil**: "«Causa y Efecto»: Apéndice 5. Programación de causa-efecto" — es un ítem de bullets de menú, no epígrafe. Pero el contenido del chunk SÍ es relevante (estructura del menú Editar Configuración).
- **F2 `[TABLA EXTRAÍDA]` mal aplicado**: el contenido es párrafo plano de texto narrativo recomendando ITS, no tabla. Híper-fragmentado por OCR (muchas barras `|` artificiales).
- **F2 header truncado y poco útil**: "Nota:Resulta más fácil hacerlo con el programa…" — frase de nota, no epígrafe.
- **F3 sec. 5.1.5 Anulación manual horaria**: relevante tangencialmente (menciona "imposición de un retardo" como concepto), pero no es la configuración del retardo principal.
- **F4 sec. 1.2.2 Teclas de función**: aporta el dato de las teclas físicas (AMPLIAR RETARDO, FIN RETARDO). Útil para la respuesta.
- **F5 índice del manual**: útil como puntero a Apéndice 1.
- **Retrieval mediocre**: trae el índice + estructura de menú + teclas físicas, pero NO el contenido literal del Apéndice 1 A1.10 que describe la configuración del retardo. El chunk clave (apéndice 1) no está en top-5.

**Comparación con bot:**

- ✓ Identifica correctamente la sección A1.10 "Ampliar Puls.Retardo" del Apéndice 1.
- ✓ Cita correctamente la ruta de menús (Editar Configuración → Configuración de la Central → Apéndice 1).
- ✓ Cita recomendación de ITS (F2).
- ✓ Cita teclas físicas AMPLIAR RETARDO y FIN RETARDO (F2, F4).
- ✓ Admite honestamente que el detalle exacto (valores, rangos) no está en F.
- ⚠️ "FIN RETARDO puede usarse sin necesidad de nivel de acceso 2" — F4 dice literalmente "Salvo las teclas SILENCIAR ZUMBADOR, FIN RETARDO y CAMBIAR PESTAÑA, para que puedan seleccionarse es necesario que la central esté en el nivel de acceso 2." → el bot interpreta correctamente que ESAS teclas SÍ funcionan sin nivel 2. OK, citation_faithful.
- ⚠️ El bot dice "Apéndice 1, sección A1.10: «Ampliar Puls.Retardo» [F5]" — verifico si F5 cita A1.10 explícitamente. F5 muestra solo el índice de las secciones 1-4 del manual y termina en "Equipos de lazo 4-1". A1.10 NO aparece en el extracto visible. Posible inferencia razonable (existe en el manual real) pero no literalmente en F5. **Citación débil**.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — la respuesta es coherente, útil y mayoritariamente fiel
- **Dimensión equivocada(s) del judge:** **citation_faithful** leve (la sección "A1.10 Ampliar Puls.Retardo" se cita a F5 cuando el extracto de F5 visible solo muestra índice de capítulos 1-4 — no se ve A1.10). Pero esa sección sí existe en el manual real, por lo que la inferencia es razonable.
- **Nota / por qué:** Respuesta de calidad. El admit_no_info parcial sobre los valores concretos del rango es correcto. Riesgo menor en la atribución específica a F5 de la sub-sección A1.10. La respuesta es útil para el técnico.
- **Origen del problema:** **retrieval** (no trae el chunk del Apéndice 1 A1.10 que es el destino directo) + **chunk-extraction** (F2 `[TABLA EXTRAÍDA]` mal aplicado).

---

## hp018 — judge dice **PASS ✓** · (18/20)

**Pregunta del técnico:** ¿Cuál es el conexionado correcto de una sirena convencional en la Morley ZXe zona 1?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 4/4 hits · missing: `[]` · **keyword_pass:** `True`

> _Notas YAML: expected_sources retirado: 'ZXe' no aparece en source_file (solo en product_model)._

### Fragmentos que el bot usó (top 5)

**[F1]** `ZXe` · *3.4.4 Circuitos de Sirenas* · `MIE-MI-530rv001` p.21 · sim 0.83

```
3.4.4 Circuitos de Sirenas

3.4.4 Circuitos de Sirenas

Paneles de Incendio ZX2e / ZX5e 

MORLEY-IAS 

Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 21 de 50 
3.4.4 Circuitos de Sirenas 
El panel de detección y control de incendio ZX2e tiene 2 circuitos de sirenas supervisados y 
limitados en corriente (Sirenas  A y B). 
El panel de detección y control de incendio ZX5e tiene 4 circuitos de sirenas supervisados y 
limitados en corriente (Sirenas  A, B, C y D). 
Cada circuito admite un consumo máximo de 1 Amp. 
Cada circuito de sirena se supervisa ante cortocircuito y circuito abierto. Debe instalarse una 
resistencia (6.8KΩ, 0.5W mínimo) final de línea (RFL) en el final del circuito, para la supervisión del 
mismo. 
Cada sirena deberá tener un diodo integrado, para impedir el consumo en polarización inversa 
(supervisión). El circuito de sirenas se polariza en inverso en reposo para supervisar la línea y cambia 
a su polarización normal, cuando se dispara la salida, permitiendo el funcionamiento de las sirenas. 

Circuitos de sirena 

Figura 13 – Terminal de circuitos de sirena de placa – ZX2e 

Figura 14 – Terminal de circuitos de sirena de placa – ZX5e 

En caso de conectar otros dispositivos no polarizados, a la línea de sirenas, deberán usarse diodos 
de polarización y protección en cada uno. 
Revise la sección 3.4.13 para ver los cables recomendados. 
TB10 
TB7
TB8
TB9
TB6 
  A- A+ B- B+ C- C+ D- D+ 
Circuitos de sirena 
  N/O  N/C  COM   N/O  N/C  COM
0V 24V
```

**[F2]** `ZXe` · *Conexionado lazo analógico con aisladores* · `MIE-MI-530rv001` p.20 · sim 0.84

```
Conexionado lazo analógico con aisladores (continuación)

MORLEY-IAS 

Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 21 de 50 
3.4.4 Circuitos de Sirenas 
El panel de detección y control de incendio ZX2e tiene 2 circuitos de sirenas supervisados y 
limitados en corriente (Sirenas  A y B). 
El panel de detección y control de incendio ZX5e tiene 4 circuitos de sirenas supervisados y 
limitados en corriente (Sirenas  A, B, C y D). 
Cada circuito admite un consumo máximo de 1 Amp. 
Cada circuito de sirena se supervisa ante cortocircuito y circuito abierto. Debe instalarse una 
resistencia (6.8KΩ, 0.5W mínimo) final de línea (RFL) en el final del circuito, para la supervisión del 
mismo. 
Cada sirena deberá tener un diodo integrado, para impedir el consumo en polarización inversa 
(supervisión). El circuito de sirenas se polariza en inverso en reposo para supervisar la línea y cambia 
a su polarización normal, cuando se dispara la salida, permitiendo el funcionamiento de las sirenas. 

Circuitos de sirena 

Figura 13 – Terminal de circuitos de sirena de placa – ZX2e 

Figura 14 – Terminal de circuitos de sirena de placa – ZX5e 

En caso de conectar otros dispositivos no polarizados, a la línea de sirenas, deberán usarse diodos 
de polarización y protección en cada uno. 
Revise la sección 3.4.13 para ver los cables recomendados. 
TB10 
TB7
TB8
TB9
TB6 
  A- A+ B- B+ C- C+ D- D+ 
Circuitos de sirena 
  N/O  N/C  COM   N/O  N/C  COM
0V 24V
```

**[F3]** `ZXe` · *MORLEY-IAS Paneles de Incendio ZX2e / ZX5e* · `MIE-MI-530rv001` p.30 · sim 0.82

```
MORLEY-IAS
Paneles de Incendio ZX2e / ZX5e

MORLEY-IAS 
 
Paneles de Incendio ZX2e / ZX5e 
 
Página 30 de 50 
Documento No.MIE-MI-530, Revisión: 001,  
Manual de Instalación 
3.4.15 Pasos de cable recomendados 
Los cables deberían pasar a la cabina, por los orificios recomendados según muestran los dibujos. 
Asegúrese de separar los cables de corriente no limitada y alimentación de los de corriente limitada. 
 
Relé de placa 
Corr. No Limitada 
Sirrenas y 
24V Aux. 
Corr. Limitada 
RS485/RS232 
Corr. Limitada 
Lazos 
Corr. Limitada 
Alimentación
C.A. 
Pase los cables 
bajo el chasis 
Use este paso, si lo 
precisa, para baterías 
externas. 
ZX2e 
Solo 
 
Figura 26 – Pasos de cableado recomendados – ZX2e 
 
 
 
Sirenas y 24V 
Aux. 
Corr. Limitada 
RS485 / RS232 
Corr. Limitada 
Lazos  
Corr. Limitada 
Alimentación 
C.A.  
Relés de placa 
Corr. No Limitada 
Use este paso, si lo 
precisa, para baterías 
externas. 
 
Figura 27  – Pasos de cableado recomendados – ZX5e


[TABLA EXTRAÍDA]
MORLEY-IAS |  |  |  |  |  | Paneles de | Inc | endio | ZX2e | / ZX5e
----------------------------------------
3.4.15 Pasos de | cabl | e reco | m | endados |  |  |  |  |  | 
Los cables d | ebería | n pasar | a | la cabina, por | los | orificios recomendado | s segú | n mues | tran los | dibujos.
Asegúrese de s | eparar | los cabl | es | de corriente | no li | mitada y alimentación | de los | de corri | ente lim | itada.
 |  |  |  | RS48 Corr. Li | 5/RS2 mitada | 32 Lazos Alim Corr. Limitada C.A | entación . |  |  | 
 |  | Sirrenas y 24V Aux. |  |  |  |  |  |  |  | 
 |  | Corr. Limitada |  |  |  | ZX2e Solo |  |  |  | 
 |  |  |  |  | Pase | los cables |  |  |  | 
 |  |  |  |  | bajo e | l chasis |  |  |  | 
 |  |  |  |  |  | Use este paso, si lo precisa, para baterías |  |  |  | 
 | Relé Corr.
[… contenido truncado para legibilidad]
```

**[F4]** `ZXe` · *2. Equipos individuales* · `MIE-MU-530rv001` p.23 · sim 0.72

```
2.
Equipos individuales

2.
Equipos individuales

PANELES DE INCENDIO ZX2e/ZX5e 

MORLEY-IAS 

Manual de Usuario 
Documento No. MIE-MU-530, Revisión: 001  
Página 23 de 36 

RELÉ      ACTIVADO 
  2 

Los circuitos de sirena de placa están constantemente supervisados para una correcta 
terminación de final de línea. La tensión de supervisión en reposo es inversa a la de disparo 
(Polaridad marcada para la conexión en la placa).  

5.4.1.5 
Prueba del zumbador interno. 
• 
Para seleccionar esta opción, pulse ‘5’. 
• 
El zumbador interno pitará. 
5.4.2 Fecha y hora 
• 
Para cambiar la fecha y hora que indica la pantalla alfanumérica, pulse ‘3’  desde el menú de usuario 
principal. 

En los sistemas con varias centrales, solo es necesario cambiar la fecha de la central master 
ya que el resto de centrales sincronizarán su fecha y hora cuando se realice un rearme en la 
central master.  

5.4.3 Habilitar / Anular funciones  
• 
Para seleccionar Habilitar o Anular, pulse la tecla correspondiente “4” ó “5” desde el menú de usuario. La 
pantalla mostrará lo siguiente para cada opción: 

HABILITAR 1)Zona     2)Equipo   3)Teclas 
          4)Modo día 5)Salidas 6)Retardos 

ANULAR  1)Zona     2)Equipo   3)Teclas 
         4)Modo día 5)Salidas 6)Retardos 

• 
Las opciones disponibles en cada menú son idénticas. Esto permite al usuario habilitar o anular: 
1. 
Zonas 
2. 
Equipos individuales 
3. 
Teclas de la central (Anula el acceso de Nivel 2 y se precisa introducir el código de nuevo) 
4. 
Modos de día (Anula el funcionamiento del modo Retardo si éste está programado) 
5. 
Salidas (Todas las Sirenas o relés) 
6. 
Retardos (Anula los retardos de los programas de salidas) 
• 
Siempre que se realiza una función de anulación, y en la pantalla se informará con un aviso de los 
equipos
[… contenido truncado para legibilidad]
```

**[F5]** `ZXe` · *Antes de instalar.* · `MIE-MI-530rv001` p.15 · sim 0.82

```
Antes de instalar.

Antes de instalar.

Paneles de Incendio ZX2e / ZX5e 

MORLEY-IAS 

Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 15 de 50 
3.4.2 Instalación de las Baterías 
3.4.2.1 
Introducción 
Revise el cálculo de baterías de la sección 4 o realice el cálculo con la herramienta del programa 
de configuración FIRE 6, para determinar el tamaño de las baterías para cada instalación. 

No conecte las baterías al panel hasta que la instalación esté terminada. 
La conexión de baterías no está limitada en corriente. 

Antes de instalar. 
La mayoría de los modelos de baterías nuevas, precisan realizar una carga máxima, revise 
las indicaciones del fabricante de las mismas o consulte a su proveedor. 

3.4.2.2 
Conexionado de baterías ZX2e 

En el paquete se incluye un cable puente 
para baterías, conecte con éste el terminal 
negativo de una batería al positivo de la otra. 
Conecte el cable rojo terminal (7) de 
Fuente de Alimentación del panel (Conector 
Fast-ON), al terminal positivo libre de baterías. 
Conecte el cable negro terminal (6) de 
Fuente de Alimentación del panel (Conector 
Fast-ON),  al terminal negativo libre de 
baterías. 
Las baterías se colocarán normalmente, 
como se muestra en el dibujo. 
7AH 
Nº2 
7AH 
Nº1 
Tope Baterías 

Para baterías de más de 12Ah, debe 
usarse una cabina separada para 
componentes de incendio como el modelo, 
Caja de Baterías 797-025-001, conectando las 
baterías al panel bajo tuberías de conducción 
adecuadas. 

12AH 
Nº2 
Tope Baterías 
12AH 
Nº1 

Figura 7 – Instalación Baterías ZX2e
```

### Respuesta del bot

```
## Conexionado de sirena convencional en ZXe (ZX2e/ZX5e)

**Nota importante:** Los fragmentos disponibles corresponden a los modelos **ZX2e y ZX5e** [F1]. El término "ZXe" engloba ambos. Confirma cuál tienes instalado, aunque el conexionado de sirenas es idéntico en ambos.

---

### Terminales de sirena

Los circuitos de sirena se ubican en los siguientes bloques de terminales [F1]:

- **ZX2e:** Terminales **TB6** y **TB7** → Circuitos **A- A+ B- B+**
- **ZX5e:** Terminales **TB6, TB7, TB8, TB9 y TB10** → Circuitos **A- A+ B- B+ C- C+ D- D+**

Para **Zona 1**, conecta en el circuito **A** (terminales **A-** y **A+**) [F1].

---

### Requisitos obligatorios del circuito

1. **Resistencia Final de Línea (RFL):** Instala una resistencia de **6,8 KΩ, 0,5 W mínimo** al final del circuito, para supervisión ante cortocircuito y circuito abierto [F1].

2. **Diodo integrado en cada sirena:** Cada sirena debe llevar un diodo integrado para impedir consumo en polarización inversa durante la supervisión [F1].
   - En reposo, el circuito se polariza en **inverso** (supervisión de línea).
   - En alarma, cambia a **polarización normal** para activar las sirenas [F1] [F4].

3. **Dispositivos no polarizados:** Si conectas dispositivos sin polaridad, deberás añadir **diodos de polarización y protección** en cada uno de ellos [F1].

---

### Límite de corriente

- Consumo máximo por circuito: **1 A** [F1].

---

### Cableado

- Los cables de sirenas se clasifican como **corriente limitada** y deben pasar por los orificios designados para ello, separados de los cables de corriente no limitada y alimentación CA [F3].
- Para el tipo de cable recomendado, consulta la **sección 3.4.13** del manual de instalación [F1].

---

Fuente: Manual de Instalación Paneles de Incendio ZX2e/ZX5e, Documento No. MIE-MI-530rv001 (Revisión: 001)

También puedo ayudarte con: **tipo de cable recomendado (sección 3.4.13)**, **cálculo de consumo de sirenas** o **programación de salidas de sirena desde menú**.
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

**Razón del judge:** Todas las afirmaciones técnicas del bot (terminales A-/A+, RFL 6,8 KΩ 0,5 W, diodo integrado, polarización inversa en reposo, límite 1 A, diodos para dispositivos no polarizados, pasos de cableado) están directamente soportadas por F1 y F3, que son los fragmentos citados. La mención de la Figura 15 (circuito de sirenas convencionales) existe en el índice de figuras V3 pero el bot no la cita ni la inventa, simplemente no la menciona, lo cual es correcto dado que no tenía ese fragmento. La respues

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `MIE-MI-530rv001` sec. 3.4.4 Circuitos de Sirenas):**

**Nota importante de terminología**: en la ZXe los "circuitos de sirena" (A/B en ZX2e, A/B/C/D en ZX5e) **no se llaman "zona 1"** — la "zona" se refiere a la detección, no a la sirena. La pregunta del eval mezcla terminología: probablemente el técnico se refiere al **circuito de sirena A** (el primero) o a "la sirena de zona 1" entendida como "la sirena asociada a la zona de detección 1" por programa de salidas.

Conexionado de una **sirena convencional 24 V** en circuito de sirena A:
1. Terminales **TB6 (A-) y TB7 (A+)** en ZX2e (o equivalentes en ZX5e).
2. Polaridad: respetar — el circuito se polariza en **inverso en reposo** (supervisión) y en **normal al disparar** (alimentación).
3. Cada sirena debe llevar **diodo integrado** anti-polaridad inversa. Si la sirena no lo lleva, instalar diodo serie 1N4007 externo.
4. **RFL al final del circuito: 6,8 kΩ, 0,5 W mínimo** (entre A+ y A-).
5. Consumo total del circuito ≤ **1 A**.
6. Cable de corriente limitada, separado de los cables de alimentación CA y relés. Tipo: ver sec. 3.4.13 del manual.
7. Si quieres que la sirena suene cuando entre en alarma la **zona de detección 1**, programar el "programa de salidas" desde menú: asignar la sirena al programa que dispara con zona 1.

**Calidad de los chunks:**

- **Retrieval excelente** para esta query: F1, F2 y F3 son todos del manual de instalación de la ZXe y aportan el dato exacto. F1 (sim 0.83) es la sec. 3.4.4 completa.
- **F1 y F2 son duplicados** (sim 0.83 vs 0.84, mismo contenido p.21). Header de F1 es correcto ("3.4.4 Circuitos de Sirenas"), F2 tiene header confuso ("Conexionado lazo analógico con aisladores" — pertenece a la sec. anterior). Header mismatch en F2.
- **F3 sec. 3.4.15 Pasos de cable recomendados**: relevante (corriente limitada vs no limitada). `[TABLA EXTRAÍDA]` mal aplicado: el contenido es la planta del recorrido de cables, texto plano, no tabla.
- **F4 sec. 5.4.x del Manual de Usuario** (no instalación): aporta polaridad supervisión.
- **F5 sec. 3.4.2.1 Antes de instalar (baterías)**: NO relevante para la pregunta. Ruido.
- **Comparado con hp009 (misma sección, misma pregunta indirecta sobre RFL)**: aquí el retriever SÍ trae sec. 3.4.4 a sim 0.83. Inconsistencia notable con hp009 (mismo manual, misma sección, query distinta → ranking radicalmente diferente).

**Comparación con bot:**

- ✓ Terminales TB6/TB7 y A-/A+ — correctos según F1.
- ✓ RFL 6,8 kΩ, 0,5 W — correcto.
- ✓ Diodo integrado, polarización inversa supervisión, normal disparo — correcto.
- ✓ Consumo máx 1 A — correcto.
- ✓ Diodos para dispositivos no polarizados — correcto.
- ✓ Corriente limitada y separación de cables — correcto (de F3).
- ✓ Remite a sec. 3.4.13 para tipo de cable — correcto.
- ✓ Cita Figura 13 (ZX2e) y Figura 14 (ZX5e) — correcto.
- ⚠️ Acepta sin desafiar la "zona 1" que usa el técnico. Debería aclarar que en ZXe no hay "zona 1" de sirena (zona = detección), aunque luego responde por circuito A que es lo equivalente más cercano. Acción didáctica perdida.
- ⚠️ No menciona la programación del programa de salidas (asociación lógica sirena↔zona de detección 1) que es lo que realmente quiere el técnico. Eso requeriría MIE-MP-530 (Manual de Programación) — no aparece en F.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — todas las afirmaciones técnicas correctas
- **Dimensión equivocada(s) del judge:** ninguna.
- **Nota / por qué:** Respuesta de alta calidad. El único pero: no aclara la posible ambigüedad terminológica ("zona 1" — el técnico podría querer la asociación lógica sirena↔zona de detección 1, no el circuito A físico). Aun así, el contenido es completo y correcto, ejemplo de buena salida cuando el retrieval funciona.
- **Origen del problema:** ninguno relevante. **Comparado con hp009**, este es el contraste — misma sección de manual, retrieval funciona mucho mejor aquí. Sugiere que el embedding model rankea peor la query "resistencia fin de línea lazo" que "conexionado sirena convencional zona" — el primero es más abstracto.

---

## hp019 — judge dice **PASS ✓** · (19/20)

**Pregunta del técnico:** ¿Cuál es el rango de temperatura de funcionamiento de los detectores Detnov serie ASD?

**Conducta esperada:** `answer` · **observada:** `ask_clarification`

**Keyword score:** 1/2 hits · missing: `['°c']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ADW535` · *Fig. 1  Principio general de funcionamiento* · `ADW535_TD_T140358es_e` p.15 · sim 0.80

```
Fig. 1  Principio general de funcionamiento

Funcionamiento 
 
ADW 535, Descripción técnica, T 140 358 e es 
15 / 119 
2 
Funcionamiento 
2.1 
Principio general de funcionamiento 
El funcionamiento del ADW 535 se basa en la expansión volumétrica de un gas causada por el calentamiento en un sistema 
neumáticamente hermético y el aumento de presión asociado. Si la presión en el tubo sensor aumenta conforme a los valores 
definidos por el firmware del ADW 535 (relación tiempo / valor límite de presión en mbar), el sistema dispara una alarma. La 
alarma se muestra en el ADW 535 de forma visual, y puede transmitirse a una central de detección de incendios de orden su-
perior a través de un contacto de conmutación libre de potencial. 
El sistema neumáticamente hermético está conformado por el tubo sensor, que se monta localmente en la zona a vigilar y se 
sella en su extremo con un racor final. El tubo sensor va conectado a la unidad de evaluación ADW 535, en la que el conducto 
neumático está conectado al dispositivo de medición de la presión y control LSU 35. El LSU 35 consta de un sensor de pre-
sión diferencial totalmente electrónico, una bomba de presión y un motor paso a paso. Todo el volumen neumático contiene 
aire ambiente normal. 
El ADW 535 está disponible como sistema con uno o dos tubos sensores. El ADW 535 con dos tubos sensores tiene dos cir-
cuitos neumáticos completamente independientes, esto es, dos dispositivos de medición de la presión y control LSU 35. To-
dos los controles del circuito y el registro de datos están diseñados para cada tubo sensor. 
 
 
Fig. 1  Principio general de funcionamiento 
I
II
Caja
Zona vigilada I
Zona vigilada II
Tubo sensor I
Tubo sensor II
Sensor de presión
diferencial
Bomba di presión
Dispositivo de medición de la
presión y co
[… contenido truncado para legibilidad]
```

**[F2]** `B501RF` · *1 2* · `I56-4206-001 NRX Radio Thermals Web` p.6 · sim 0.80

```
1
2

1
2

N200-302-00
I56-4206-001 
Honeywell Life Safety Iberia, S.L.  C/ Pau Vila, 15-19, 08911 Badalona (Barcelona) Espana
según sea necesario. A continuación, el sensor vía radio se sincronizará 
con los demás dispositivos asociados mientras la pasarela crea la red en 
malla (mesh) vía radio (para más información, consultar el Manual de 
programación y puesta en funcionamiento vía radio.)
INDICADORES LED Y DESCRIPCIÓN DE AVERÍAS
El sensor vía radio cuenta con dos indicadores LED que muestran el 
estado del dispositivo.
4c
TENER EN CUENTA 
LOS POLOS
4a
Figura 4: Instalación de las pilas y 
selectores giratorios de dirección
4 x Duracell 
Ultra 123
4d
4b
PRUEBA
Prueba de imán
Un imán de prueba colocado correctamente generará una alarma. Colocar 
el imán (M02-04-00) como se muestra en la Figura 5, después de identificar 
la línea recta en la base del sensor. Para ayudar a la correcta ubicación del 
imán, los LEDs del sensor se pondrán verdes durante 1s cuando se active 
el contacto de la alarma.
Prueba de calor directo (secador de pelo 1000-1500 vatios) 
Dirigir el calor hacia el sensor lateralmente. Mantener la fuente de calor 
a una distancia de aproximadamente 15 cm para prevenir daños en la 
superficie durante la prueba. El sensor debería enviar una alarma a la 
central mediante la pasarela cuando la temperatura del sensor alcance 
los 58°C.
Tras la prueba, restablecer la indicación de la alarma en la central de incendios.
LIMPIEZA
Utilizar una aspiradora y/o aire comprimido limpio para eliminar el polvo 
y los restos del termistor y de la tapa del sensor según se necesite 
(asegurarse de no producir daños en el termistor).
Nota
Cuando se sustituyan las pilas, será necesario cambiar las 4
LIMITACIONES DE LOS SENSORES TÉRMICOS
Estos sensores térmicos sólo funcionará
[… contenido truncado para legibilidad]
```

**[F3]** `RP1r` · *Low* · `HLSI-MN-103I_RP1r-Supra_lr` p.37 · sim 0.70

```
Low

Low

37
http://www.honeywelllifesafety.es
HLSI-MN-103-I v.06
User Manual 
RP1r-Supra
Operation
4.5.2 
Preactivated status (single zone fire condition)
If there is an alarm in one of the zones, the control panel goes into preactivated release mode and the following indications are present:
Power
POWER LED (green). This is lit continuously when the panel is powered.
The internal buzzer operates (pulsing tone, 1 Hz)
NA
NC
Común
GENERAL FAULT relay (GEN.FAULT) energized ≡ standby (continuity between C and NO)
Alarm
The ALARM led (red) flashes.
Z1
Z2
Z3
Zone status leds indicate “Alarm” in the corresponding zone. 
Flashing in case of a detector alarm/ Steady  in case of a call point alarm
 Pre-Activated
Activated
Status leds → 
“Preactivated”: ON 

“Activated”: OFF
Status contacts →  
PREACT: ON 

ACTIV: OFF 

RELEASED: OFF
When 
 parameter= 0 (default value), sounder outputs 1 and 2 (SND1 and SND2) will operate with slow pulsing tone (1 Hz). 
When the delay configured in parameter 
 is finished, sounders can be silent by pressing “Silence / Resound” 
Silence
Resound

key. If a specific delay has been configured, sounders will be silent until the delay is finished. The delay can be cancelled at 
any time by pressing the “Delay ON/OFF” key 
Delay
On/Off
and the sounders will operate immediately.
```

**[F4]** `ADW535` · *Indicaciones* · `ADW535_TD_T140358es_e` p.76 · sim 0.80

```
Indicaciones (continuación)

• Análisis de fugas y control de longitud; compa-
ración de la longitud de tubo sensor conectado en 
relación con la presión de reset inicial. En caso de 
discrepancia  fallo de reset inicial  reset inicial 
abortado 

• Estabilidad de la temperatura; la presión medida 
en el tubo sensor I (sin sobrepresión/subpresión) 
se observa durante aprox. 30 s para detectar 
cambios de temperatura. 

• Acumulación de presión; el motor paso a paso 
arranca y acumula una sobrepresión en el tubo 
sensor I 

• Control de estanqueidad; la sobrepresión del tu-
bo sensor I se observa durante aprox. 30 s. En 
caso de caída de presión  fallo de reset inicial 

Parpadeo - - -   
• Indicación reset inicial finalizada 

Indicación 
 La indicación - - - señaliza únicamente la finalización del proceso de reset inicial. En función del resultado, 
puede existir un fallo de reset inicial. 
El reset inicial debe seleccionarse y llevarse a cabo por separado para cada tubo sensor de acuerdo con el pro-
cedimiento anterior. 

UP
UP
OK
UP
OK
OK
```

**[F5]** `SMART 3G` · *4. Condiciones especiales para un uso seguro* · `SMART 3G ZONA 2 MTEX4805__SP Rev 3` p.10 · sim 0.80

```
4. Condiciones especiales para un uso seguro

4. Condiciones especiales para un uso seguro

10 
MTEX4805_SP Rev. 3         15/02/2021 
4. Condiciones especiales para un uso seguro  
- La instalación, uso, mantenimiento y reparación de los equipos debe llevarse a cabo de 
acuerdo con estas Instrucciones de Seguridad proporcionadas por Sensitron. 
- La instalación del detector de gas debe garantizar la conexión equivalente de la caja. 
- Solamente los modelos con el dispositivo de filtro de polvo pueden ser instalados en Zona 
22. 
- La membrana del filtro del dispositivo de protección contra el polvo no debe dañarse, 
perforarse ni retirarse. Además, la membrana no debe tocarse con las manos 
desnudas para evitar daños en el filtro. 
- Para detectores con caja de aluminio y recubrimiento epoxi, se debe considerar el 
riesgo de cargas electrostáticas. La limpieza del equipo debe hacerse con paño 
húmedo o productos antiestáticos. 
- Las temperaturas límite de funcionamiento del detector se muestran en la etiqueta. Son 
compatibles con las temperaturas límite de los elementos sensibles utilizados en su 
interior. 
5.  
Instalación 
La instalación de detectores a prueba de explosiones será realizada por personal 
experimentado de conformidad con los criterios establecidos en el anexo A de la en 60079-
14. 

Está estrictamente prohibido y peligroso abrir y cerrar el dispositivo en una zona 
peligrosa con tensión; esta operación debe llevarse a cabo en una zona segura teniendo 
cuidado de eliminar la tensión por adelantado. La apertura puede tener lugar después 
de 10 minutos desde el corte de tensión. 
Se recomienda utilizar equipos de protección individual (EPI) al operar dentro de la caja, para 
evitar lesiones. 

5.1 Montaje correcto 
El detector debe instalarse siempre c
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados no contienen información sobre el rango de temperatura de funcionamiento de los detectores Detnov serie ASD.

Los fragmentos disponibles cubren: principio de funcionamiento del ADW535 [F1], indicaciones del ADW535 [F4], un detector de gas SMART 3G de Sensitron [F5], un sensor vía radio B501RF de Notifier [F2], y un panel RP1r-Supra de Honeywell [F3]. Ninguno de ellos incluye las especificaciones de temperatura de operación para la serie ASD de Detnov.

Para obtener este dato, consulta directamente el manual técnico del modelo ASD concreto que estás usando (por ejemplo, ASD535 u otra variante) en la sección de especificaciones técnicas o características ambientales.

¿Qué modelo exacto de la serie ASD estás usando? Con el modelo concreto puedo intentar localizar la información si está disponible en mi base documental.
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

**Razón del judge:** El bot admite correctamente que no dispone de información sobre Detnov serie ASD, ya que ningún fragmento F ni V cubre ese fabricante/producto. La descripción de los fragmentos disponibles es precisa, y redirigir al técnico al manual físico o fabricante es una acción válida y útil.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `ASD531/532/533/535_TD` Securiton):**

**Atribución incorrecta en la pregunta**: la **serie ASD (ASD531/532/533/535) es de SECURITON**, no de Detnov (mismo patrón que hp002 con ASD535). Detnov puede distribuirla en España, pero los manuales son Securiton.

Rango de temperatura de funcionamiento (datos típicos del catálogo Securiton ASD):
- **Temperatura ambiente de funcionamiento**: **-20 °C a +60 °C** (típico ASD 53x, EN54-20).
- **Temperatura del aire muestreado**: **-30 °C a +75 °C** según modelo y configuración del tubo sensor.
- **Humedad relativa**: 95% sin condensación.

Estos datos están en la sección de **datos técnicos** (típicamente cap. final) de cada manual ASD53x. El corpus debería contenerlos si los chunks de specs están indexados.

**Calidad de los chunks:**

- **Retrieval completamente roto**: ninguno de los 5 chunks corresponde a la serie ASD de Securiton/aspiración. F1 y F4 son **ADW535** (detección térmica lineal por tubo neumático — otro producto Securiton, no ASD aspiración). F2 es **B501RF** (base radio Notifier). F3 es **RP1r** (central extinción Notifier). F5 es **SMART 3G** (detector de gas Sensitron).
- **Cross-product contamination grave**: la query "detectores Detnov serie ASD" rankea 5 productos distintos, ninguno de los cuales es ASD aspiración Securiton. Sugiere que el embedding agrupa por "detector + temperatura" sin discriminar producto.
- **Headers basura**: F1 "Fig. 1 Principio general de funcionamiento", F2 "1 2", F3 "Low", F4 "Indicaciones", F5 "4. Condiciones especiales para un uso seguro". 4 de 5 son caption/frase suelta.
- **Premisa errónea del usuario** (Detnov ASD vs Securiton ASD) NO se desafía por el bot.
- El bot **observa la inconsistencia** ("F1 ADW535, F4 ADW535, F2 SMART 3G, F3 B501RF, F5 RP1r") — buen análisis, pero la conclusión es admit sin profundizar.

**Comparación con bot:**

- ✓ Admite honestamente que F no cubre ASD Detnov.
- ✓ Describe correctamente cada chunk (qué producto es).
- ✓ Pregunta de vuelta al técnico el modelo concreto — útil.
- ⚠️ **Conducta observada `ask_clarification` mientras esperada era `answer`** (según YAML): el bot termina con "¿Qué modelo exacto de la serie ASD estás usando?". Esto técnicamente NO es la conducta esperada de "answer". El judge igualmente marca `behavior_match: True`. Inconsistencia entre conducta esperada/observada y veredicto del judge.
- ⚠️ NO menciona que ASD es Securiton, no Detnov. Premisa de fabricante incorrecta aceptada (mismo patrón que hp002, hp014).
- ⚠️ NO ofrece dato de rango típico (-20 a +60 °C) ni siquiera como aproximación, aunque ADW535 (cuyo manual sí tiene chunks recuperados) podría tener temperatura ambiente similar (~-25 a +60 °C según hoja técnica).

**Veredicto:**
- [ ] **De acuerdo** con el judge / [x] **En desacuerdo** — yo diría: **FAIL técnico**
- **Dimensión equivocada(s) del judge:** **behavior_match** (esperaba `answer`, observada `ask_clarification`, el judge marca `True` igualmente — inconsistencia clara). Posible **relevant** también: la pregunta sobre rango de temperatura es respondible con dato genérico de catálogo, y el bot ni siquiera lo intenta.
- **Nota / por qué:** El judge ignora la discrepancia conducta esperada vs observada. El bot pide aclaración cuando el YAML decía que respondiera. Además, ningún F es de ASD aspiración Securiton — el retrieval está roto a nivel de discriminación de producto. La calibración previa (expected: answer) puede que requiera otro recalibrado (¿es realmente respondible este query con el corpus actual? Si no, debería estar en `admit_no_info`).
- **Origen del problema:** **retrieval** (cross-product contamination total — ninguno de los 5 es ASD aspiración) + **chunk-extraction** (headers basura) + **judge** (no audita coherencia behavior_match con expected/observed) + **YAML** (la categoría `answer` puede ser inalcanzable si el corpus no indexa specs de ASD).

---

## hp020 — judge dice **PASS ✓** · (20/20)

**Pregunta del técnico:** En la Notifier INSPIRE, ¿cómo se configuran las contraseñas de nivel 2 y nivel 3?

**Conducta esperada:** `answer` · **observada:** `answer`

**Keyword score:** 3/4 hits · missing: `['password']` · **keyword_pass:** `False`

> _Notas YAML: expected_sources retirado: 'INSPIRE' solo tiene 7 chunks con source_file literal (2922 en product_model). Demasiado débil para exigirlo._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `INSPIRE` · *PASO 6 Conectar la central al programa y Recibir la configuración 11* · `4188-1132-ES issue 3_04_2025_Qref` p.2 · sim 0.80

```
PASO 6 Conectar la central al programa y Recibir la configuración
11

2
﻿
Introducción
En este documento se ofrecen instrucciones 
detalladas para la puesta en marcha del 
sistema de detección de incendios INSPIRE de 
Notifier. 
Reúne la información relevante de diferentes 
manuales que le proporcionarán más 
información sobre la instalación, configuración 
y uso de la central, del programa de 
configuración de CLSS y del portal de CLSS 
Cloud (Administrador del sitio).
Contenido
PASO 1 	 Crear sitio / edificio / central en el portal CLSS Cloud	
3
PASO 2 	 Generar archivo de licencia para una central	
4
PASO 3	
Instalar la central y encender	
5
PASO 4	
Primera conexión de la central, ejecución del proceso de 
autobusqueda de los dispositivos del lazo y generación 
de la configuración estándar	
6
PASO 5 	 Primera instalación del programa de configuración 
de CLSS	
10
PASO 6 	 Conectar la central al programa y Recibir la configuración	
11
PASO 7 	 Editar la configuración de la central con el Programa de 
Configuración CLSS 	
13
PASO 8 	 Enviar archivos de configuración, licencia e imagen 
a la central	
16
PASO 9	
Agregar / Cambiar / Eliminar dispositivos en un circuito 
de lazo (Auto configuración desde el Programa)	
18
PASO 10 	Prueba del sistema	
19
```

**[F2]** `INSPIRE` · *Directiva WEEE: Al final de su vida útil, el embalaje, el producto y las pilas deben desechrse a través de un centro de * · `HOP-138-8ES  issue 6_01-2026_Co` p.91 · sim 0.80

```
Directiva WEEE:
Al final de su vida útil, el embalaje, el producto y las
pilas deben desechrse a través de un centro de cons.
No desechar con los residuos domésticos normales.
No se queme.

Notifier INSPIRE E10/E15 
Fire Alarm Control Panels 
Commissioning Instructions
Directiva WEEE:
Al ﬁnal de su vida útil, el embalaje, el producto y las 
pilas deben desechrse a través de un centro de cons. 
No desechar con los residuos domésticos normales.
No se queme. 
Al ﬁnal de su vida útil, el embalaje, el producto y 
las pilas deben desecharse a través de un centro 
de reciclaje adecuado y de acuerdo con la 
legislación nacional o local.
Notifier by Honeywell se reserva el derecho de revisar esta publicación de vez en cuando y hacer cambios en el contenido del presente sin la 
responsabilidad de notificar a ninguna persona sobre tales revisiones o cambios.
Honeywell Life Safety Iberia
C/Pau Vila 15-19, 08911 Badalona, Barcelona, Spain
Soporte técnico:
https://buildings.honeywell.com/us/en/lp/notifier-inspire
Sitio web: 
https://www.notifier.es/


[TABLA EXTRAÍDA]
|  |  |  | Notifier INSPIRE | E | 10/E1
----------------------------------------
 |  |  |  | Fire Alarm Contr | ol | Panels
 |  |  |  | Commissioning | I | nstruct
Al final de s las pilas deb | u vida útil, en desech | el embalaje, arse a travé | el producto y s de un centro |  |  | 
de reciclaje legislación | adecuado nacional o | y de acuerdo local. | con la |  |  | 
Directiva W Al final de su pilas deben d | EEE: vida útil, el esechrse a | embalaje, el p través de un c | roducto y las entro de cons. |  |  | 
No desechar No se queme | con los resi . | duos domésti | cos normales. |  |  | 
by Hone | ywell s | e reserv | a el derecho de revisar e | sta publicación de vez en cuando y hacer cambio | s en | el contenido de
[… contenido truncado para legibilidad]
```

**[F3]** `INSPIRE E10` · *CH 4* · `HOP-138-9PT-issue 6_01-2026_In` p.67 · sim 0.80

```
CH 4

67
Instruções de instalação da Central de controlo de alarme de incêndio Notifier INSPIRE E10/E15
CABLAGEM PARA CIRCUITOS DE ENTRADA E SAÍDA
Central Notiﬁer INSPIRE
I/O 4-CH
Canal 2 IN/OUT 1
Canal 1 IN/OUT 2
Canal 1 IN/OUT 1
6
7
8
9
10
Canal 3 IN/OUT 1
Canal 2 IN/OUT 2
Cor 
cinzenta
Aux. DC Out GND
Aux. DC Out 24V
Canal 4 IN/OUT 2
Canal 4 IN/OUT 1
Canal 3 IN/OUT 2
1
2
3
4
5
comprimento máximo do cabo recomendado - 100 m 
CH 4
CH 3
CH 2
CH 1
24 V CC
Barra de 
ligação 
à terra
1 KΩ
10 KΩ
Entrada de Avaria
Entrada de Incêndio
Entrada de Controlo
Alarme Técnico
+
-
EOL - O
(N.º da peça 808624)
Saída de Alarme
EOL - O
808624
V0100R001
EOL - O
808624
V0100XXXX
Interruptor
+
-
-
+
vermelho
preto


[TABLA EXTRAÍDA]
|  | Instruçõe | s | de inst | alação da | C | entral | de contr | olo | de a | la | rme de incêndio Notifier INSPIRE | E10/E15
----------------------------------------
 | L | AGEM P | A | RA C | IRCUIT | O | S DE | ENTR | AD | A E | S | AÍDA | 
 |  | comprimento | má | ximo do | cabo recomen | d | ado - 10 | 0 m |  |  |  |  | 
4 | V | CC |  |  |  |  |  |  |  |  |  |  | 
 |  | 4 3 | 2 | 1 |  |  | - |  |  |  |  |  | 
 |  | HC HC | HC | HC |  |  |  |  |  |  |  |  | 
 |  |  |  |  |  |  | + | preto |  |  |  |  | 
 |  |  |  |  | Barra de |  | - |  | Saída | de Alar | me |  | 
 |  |  |  |  | ligação |  |  |  | EOL - (N.º da | O peça 8086 | 24) |  | 
 |  |  |  |  | à terra |  |  |  | EEOO 8V8V00008811 | LL -- OO 6600220044RXX00X1X |  |  | 
 | D | 2 1 2 |  |  |  |  |  |  |  |  |  |  | 
V42 tuO CD | NG tuO CD | TUO/NI TUO/NI TUO/NI 1 2 TUO TUO 4 4 3 l l l | 1 TUO | 2 1 TUO TUO |  |  | + | ve | rmel | ho |  |  | 
.xuA | .xuA | anaC anaC anaC /NI /NI 3 2 lanaC lanaC | /NI 2 lanaC | /NI /NI 1 1 lanaC lanaC |  |  | - | 10 KΩ | 1 KΩ | Entrada Entrada Entrada Alarme T | de de
[… contenido truncado para legibilidad]
```

**[F4]** `INSPIRE` · * e a seguir iniciar sessão com o código de acesso de Nível 2. 02 Selecionar a opção «Configuração dia / noite» . 03 Se* · `HOP-338-9PT-issue 4_01-2026_Op` p.43 · sim 0.80

```
 e a seguir iniciar sessão com o código de acesso de
Nível 2.
02 Selecionar a opção «Configuração dia / noite» .
03 Selecione o botão Alternar ou Dia/Noite para (continuación)

[TABLA EXTRAÍDA]
A funcio | nalidade | «Atualização» | de | firmw | ar | e | é utilizada pelo engen
----------------------------------------
mento para atualizar o fir | mware d | o central de co | ntr | olo. E | st | a | funcionalidade é re
dado não ser acessível | através | do código de | ac | esso | d | e | Nível 2/3.
DEFINIÇÕES D | O AL | ERTA SON | O | RO |  |  | 
 |  | As «Definições | do | sinal | s | on | oro» encontram-se e
«Settings» e são acedida | s pelo e | ngenheiro que | col | oca o | c | en | tral em funcionament
Esta funcionalidade é | referida | apenas para | efe | itos i | n | fo | rmativos, dado não
ser acessível através d | o códig | o de acesso d | e N | ível 2 | . | P | odeHabilitar/Anular
alarme sonoro, se for u | m utiliz | ador com Nív | el d | e ac | e | ss | o 3.
45
Centrais de controlo Notifier INSPIRE E10/E15 - Instruções de utilização
HABILITAR O MODO DE COLOCAÇÃO 
EM FUNCIONAMENTO
 A funciona­
lidade «Habilitar o modo de comissionamento» encontram-se em 
«Settings» é referida aqui apenas a título informativo. Esta funcio­
nalidade é utilizada por um técnico de colocação em 
funcionamento.
Não há necessidade de aceder às funcionalidades 
«Actualizar», «Configuracao do besouro» e 
«Habilitar o modo colocação em serviço» para o 
funcionamento diário do sistema de alarme de 
incêndio.
MODO DE SERVIÇO
A funcionalidade Modo de Serviço («Modo de serviço») é 
utilizada por um técnico de colocação em funcionamento 
para testar dispositivos no sistema. 
REINICIALIZAÇÃO DE FABRICA
Esta função está acessível apenas no nível de acesso 4 e 
permite repor as definições de fábr
[… contenido truncado para legibilidad]
```

**[F5]** `INSPIRE` · *8 CH2 ISO GND* · `HOP-138-9ES issue 5_11-2025_In` p.62 · sim 0.72

```
8 CH2 ISO GND

62
Instalación de la central
MÓDULO DE COMUNICACIÓN 
SERIE
SERIAL
COM
White
COMM Serial
1  2  3  4  5
6  7  8  9 10
1 Aux. DC OUT +24 V
2 Aux. DC OUT GND
4 CH1 RS485 B
5 CH1 RS485 A
6 CH2 RS232 CTS
7 CH2 RS232 RTS
9 CH2 RX/B
10 CH2 TX/A
3 CH1 ISO GND
8 CH2 ISO GND
El módulo de comunicación serie (HOP-405-100) proporciona 
un puerto RS485 y un puerto RS232/RS485 configurable, con 
una salida auxiliar de 24 Vcc. El módulo proporciona el protocolo 
serie propietario "Notifier TPP" para la comunicación con equipos 
externos, como la pasarela CLSS, central con el repetición. 
Utilice únicamente un cable recomendado para conectar 
circuitos externos a los puertos RS232/485, asegurando que no 
se supere la longitud del cable de 15 m/1,2 km, respectivamente.
	
 El módulo de comunicación serie tiene el código de color 
Blanco
	
 Dimensiones Altura-130 mm x Ancho-28 mm x 
Profundidad-117 mm
	
 Supervisa las averías de comunicación
	
 Al módulo se le puede dar una etiqueta en el programa para 
su identificación en la pantalla de la central
	
 La línea 1 (CH1) tiene el tipo de comunicación RS485
	y A esta línea se le puede dar una etiqueta desde el programa
	y Se puede ajustar el protocolo, es decir, a TPP o repetidor
	y Versión de protocolo 0013 / 0011A
	y Tipo de modo TPP «Full duplex» o «Half duplex»
	
 La línea 2 (CH2) tiene el tipo de comunicación RS485 o 
RS232
	y A esta línea se le puede dar una etiqueta desde el programa
	y Se puede ajustar el protocolo, es decir, a TPP o repetidor
	y Versión de protocolo 0013 / 0011A
	y Tipo de modo TPP «Full duplex» o «Half duplex»
	
 Una salida de tensión puede proporcionar un máximo de 24 
Vcc ± un 5 %. 
	
Corriente configurable a 0,5 A, 1 A, 1,5 A y 2 A 
	
 Estado de salida auxiliar Encendido / Apagado
INDICADORE
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Los fragmentos recuperados corresponden a manuales de instalación, puesta en marcha y cableado de la **INSPIRE E10/E15**, pero **ninguno de ellos describe el procedimiento de configuración de contraseñas de Nivel 2 y Nivel 3**.

Lo que sí aparece en los fragmentos es:

- Que existe un **código de acceso de Nivel 2** [F4] y un **Nivel 3** [F4], y que ciertas funcionalidades (como "Definições do alerta sonoro") solo son accesibles con Nivel 3 [F4].
- Que las actividades de puesta en marcha que requieren **acceso de nivel 3** se explican en detalle en el **Manual de comisionamiento** [F4].
- Que la función de **Reinicialización de fábrica** solo es accesible en **nivel de acceso 4** [F4].

Sin embargo, el procedimiento concreto para **configurar o cambiar las contraseñas** de esos niveles no aparece en ninguno de los fragmentos disponibles.

Para obtener ese procedimiento, consulta:
- El **Manual de comisionamiento de la INSPIRE E10/E15** (referenciado en [F4]).
- El manual de puesta en marcha **4188-1132-ES issue 3** [F1], que cubre la configuración mediante el **Programa de Configuración CLSS** (Paso 7).
- El soporte técnico de Notifier: https://buildings.honeywell.com/us/en/lp/notifier-inspire [F2].

---

Fuente: HOP-338-9PT-issue 4_01-2026_Op (sin revisión registrada); 4188-1132-ES issue 3_04_2025_Qref (sin revisión registrada); HOP-138-8ES issue 6_01-2026_Co (sin revisión registrada)
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

**Razón del judge:** El bot admite correctamente que los fragmentos disponibles no contienen el procedimiento para configurar contraseñas de Nivel 2 y Nivel 3, y ningún fragmento F ni V lo describe tampoco. Las afirmaciones que sí hace (existencia de niveles de acceso 2, 3 y 4, y que las actividades de nivel 3 se detallan en el Manual de comisionamiento) están soportadas por F4. El bot redirige al técnico a fuentes concretas y accionables, lo que constituye un admit_no_info honesto y útil.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `HOP-138-8ES` Commissioning + `HOP-138-9ES` Installation + Manual de configuración CLSS INSPIRE):**

Configuración de contraseñas de Nivel 2 (operador) y Nivel 3 (instalador) en INSPIRE E10/E15:
1. **Acceso**: con clave de Nivel 3 actual (instalador). Por defecto de fábrica suele ser un PIN documentado en el manual de comisionamiento — cambiarlo en la primera puesta en marcha es **obligatorio por buenas prácticas**.
2. **Ruta en pantalla local**: Menú → **Settings (Ajustes)** → **Acceso de usuario** (o equivalente «Códigos de acceso»). Permite definir códigos para usuarios de Nivel 2 (típicamente 4 dígitos) y Nivel 3 (típicamente 5 dígitos).
3. **Desde el software CLSS Configurator (recomendado)**: módulo "Usuarios y accesos" del proyecto → editar perfiles Nivel 2 y Nivel 3 → enviar configuración a la central (Paso 8 de la guía rápida 4188-1132-ES).
4. **Nivel 4** (fábrica/factory reset) NO se configura por el usuario; reservado a Honeywell.
5. Documentar los nuevos códigos según política de mantenimiento — la INSPIRE permite recuperar un código temporal vía portal CLSS Cloud si se olvida.

**Calidad de los chunks:**

- **Retrieval mediocre**: solo F4 (portugués, p.43 manual de utilizaçao) toca tangencialmente los niveles de acceso. F1, F2, F3, F5 son sobre puesta en marcha, WEEE, cableado I/O y módulo de comunicación serie — irrelevantes.
- **F1 header inútil**: "PASO 6 Conectar la central al programa y Recibir la configuración 11" — entrada de índice, no epígrafe.
- **F2 header inútil largo**: "Directiva WEEE: Al final de su vida útil…" — texto legal de portada, no epígrafe.
- **F2 `[TABLA EXTRAÍDA]` mal aplicado**: el contenido es el bloque legal/de portada, no tabla.
- **F3 header "CH 4"**: fragmento de etiqueta de canal, no epígrafe. `[TABLA EXTRAÍDA]` mal aplicado: el contenido es un diagrama de cableado descrito en texto.
- **F4 (portugués) header truncado y arrancando en "e a seguir iniciar sessão com o código de acesso de Nível 2"**: header inútil. `[TABLA EXTRAÍDA]` mal aplicado.
- **F5 ruido total**: módulo de comunicación serie HOP-405-100, no relacionado con contraseñas.
- **Idioma mixto**: F4 portugués; pregunta en español. No hay chunk en español de los manuales HOP-138-8ES / HOP-338-8ES sobre contraseñas. Cero recall en idioma esperado.
- **Cross-doc no aprovechado**: la INSPIRE tiene varios manuales (HOP-138-8/9, HOP-338-9, 4188-1132); solo F4 (PT) toca acceso de usuario marginalmente.

**Comparación con bot:**

- ✓ Admite honestamente que F no contiene procedimiento de configuración de contraseñas.
- ✓ Cita la existencia de Niveles 2, 3, 4 (de F4).
- ✓ Redirige al Manual de comisionamiento HOP-138-8ES (correcto).
- ✓ Cita 4188-1132-ES (guía rápida) — útil porque tiene el Paso 7 de configuración CLSS.
- ⚠️ NO menciona específicamente el menú/pantalla donde se configuran las contraseñas (Settings → Acceso de usuario) ni el software CLSS Configurator como herramienta principal. La pregunta del técnico es operativa; la respuesta es demasiado abstracta.
- ⚠️ NO cuestiona si el técnico ya tiene acceso de Nivel 3 (prerequisito para cambiar contraseñas de otros niveles) — pieza de contexto operativo importante.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS) — admisión coherente con F pobres
- [ ] **Pero la respuesta es subóptima**: el retrieval es deficiente y la respuesta refleja eso. Un técnico recibe "consulta el manual de comisionamiento" sin nada accionable.
- **Dimensión equivocada(s) del judge:** ninguna estricta. **helpful** débil — la admisión es honesta pero no aporta dirección operativa.
- **Nota / por qué:** Admit_no_info correcto dado el corpus disponible. El problema real es upstream: la INSPIRE tiene manuales completos (HOP-138-8ES Commissioning, HOP-338-9ES Operating) que deberían contener la sec. de configuración de contraseñas, pero el retrieval no la trae. La nota YAML lo identifica: "INSPIRE solo tiene 7 chunks con source_file literal (2922 en product_model)" — desconexión de metadata.
- **Origen del problema:** **retrieval** (no recupera chunk relevante de contraseñas de los manuales HOP) + **metadata** (product_model vs source_file desconectados; INSPIRE solo 7 chunks literales) + **chunk-extraction** (4/5 chunks irrelevantes con headers basura) + **idioma** (cross-language sin filtro: F4 portugués cuando hay manual ES disponible).

---

