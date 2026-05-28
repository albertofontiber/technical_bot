# Calibración del judge v2 — categoría `missing_context` (8 preguntas)

**Origen:** `logs/eval_20260502T152857Z.json` (eval del 2 mayo 2026).

**Categoría:** Técnico no menciona fabricante/modelo -> bot debe pedir aclaración.

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

## mc001 — judge dice **PASS ✓** · (1/8)

**Pregunta del técnico:** Tengo una alarma de batería baja que no se quita aunque las baterías son nuevas

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 3/3 hits · missing: `[]` · **keyword_pass:** `True`

### Fragmentos que el bot usó (top 5)

**[F1]** `unknown` · *1. Para la entrada de red y las salidas de CC + alarmas, utilice orificios separados en la parte inferior* · `MA-AL-T500-01-07 Manual TUL500esp rev1` p.3 · sim 0.77

```
1. Para la entrada de red y las salidas de CC + alarmas, utilice orificios separados en la parte inferior (continuación)

El voltaje de la batería se monitorea continuamente, si el voltaje cae por debajo de V (B) low = 20,8 V, el 
relé “GUASTO” (FALLO) se enciende y el panel frontal “Battery Low” se enciende. Si la 
tensión cae por debajo de V (B) min = 19,8 V, la batería se aísla para evitar la descarga 
profunda. Una vez que la batería se desconecta. La batería se conectará al sistema si el 
voltaje es superior a 16 V. 
La resistencia interna de la batería se prueba cada 2,5 horas como mínimo. Si la resistencia es superior a 1 
ohmio, aparece una advertencia. El LED "Failure" (Fallo) del panel frontal se enciende, el LED 
" Overcharged battery” (Batería sobrecargada) parpadea lentamente y el DL1 interno 
parpadea rápidamente. 
Monitorización del fusible de la batería, en caso de avería del fusible, el LED “Low Battery” (Batería baja) 
comienza a parpadear lentamente. Cuando se reemplaza el fusible, la señal desaparece. 
Monitoreo de fusibles, si un fusible se abre, el LED se enciende, cuando la causa de la falla desaparece, el 
LED se apaga. 
Monitorización de la red, cuando falta la red, el LED del panel frontal "Mains” (Red) se apaga y el relé 
"RETE" está activado. Cuando se enciende el LED de retorno de red "Red" y se restablece el 
relé "RETE". 

SERVICIO 

El servicio periódico programado debe ser realizado por personal calificado para evitar la posibilidad de un 
mal funcionamiento de la fuente de alimentación. Se recomienda realizar revisiones cada 6 meses y evaluar 
el panel de control del sistema para comprobar posibles alarmas durante las pruebas. 

- Verifique las conexiones de las líneas de alimentación 230 V ~ 
- Verifique las conexiones de las líneas de
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *Tengo avería de resistencia de baterías en central DXc* · `Averia-de-resistencia-de-baterias-en-central-DXc` p.1 · sim 0.80

```
Tengo avería de resistencia de baterías en central DXc

Tengo avería de resistencia de baterías en central DXc
Question Tengo avería de resistencia de baterías en central DXc,
 
Answers Para comprobar la lectura de baterías que esta haciendo la central, realice los siguientes pasos:
1- Entrar en opción 5 “Menu”.
 
2- Introducir clave 
 + OK.
“1234”
 
3- Entrar en opción 4 
.
“Ver”
 
4- Entrar en opción 7 
.
“Voltajes”
 
5- Bajar con flecha hacia abajo hasta ver “Resist Baterías”
 
El valor que se visualiza es la resistencia interna de las baterías, si este valor no esta comprendido
entre 
 hay que sustituir las baterías por estar desgastadas o por no cumplir la
200 - 5
 mohmios,
00
normativa (resistencia interna alta)
Si usted tiene la certeza, que las baterías están bien de carga y la resistencia interna es la adecuada,
el problema puede estar en el circuito de supervisión de baterías de la central. En ese caso deberá
enviar la central a reparar o sustituir la central.
Características de las baterías 7Ah suministradas por HFS
Capacidad nominal (Ah)           NP 7-12
20 hr a 1.75 vpc 30ºC                      7
10 hr a 1.75 vpc 20ºC                     6.4
5   hr a 1.75 vpc 20ºC                     5.9
1   hr a 1.75 vpc 20ºC                     4.2
Voltaje                                          12
Densidad de energía (Wh.L.20hr)    91
Energía especifica (Wh.kg.20hr)      32
Resistencia interna (m.Ohms)          25
Descarga Máxima (A)                    40/75
Corriente de cortocircuito (A)          210
Para cualquier consulta técnica no dude en acudir al servicio de soporte técnico de Honeywell a
través del correo electrónico, soporteHLSI@Honeywell.com
```

**[F3]** `NFS Supra` · *=OFF= No se indican las Averías de baterías.* · `HLSI-MN-025_NFS Supra` p.45 · sim 0.70

```
=OFF= No se indican las Averías de baterías.

=OFF= No se indican las Averías de baterías.

NFS Supra 

Configuración especial 
 45 

HLS-MN-025 v.05 

            Manual de usuario 
www.honeywelllifesafety.es 
5.5.1 Ver/Cambiar configuración de las Funciones especiales: 
Apague completamente el panel (alimentación principal y baterías), ponga el puente de 
programación (PROG) y alimente el panel normalmente, se iluminarán los leds de las funciones 
especiales indicando la configuración como se indica a continuación: 
Led Teclado  
= ON  = Averías enclavadas. Las averías precisan 
REARME del panel (por defecto)  

=OFF =Averías Rearmables. Las averías se rearman  
automáticamente al desaparecer la misma. 

Led  Silenciar Sir. 
=ON  
= Se indica la Avería de alimentación 
principal (por defecto) 
=OFF = No se indican las Averías de alimentación 
principal.  

Led Retardo Sí/No 
=ON = Se indica avería de baterías (por defecto)  

=OFF= No se indican las Averías de baterías. 

Led Silenc. Zumb. 
=OFF= Las sirenas no se reactivan con cada nueva 
alarma 

=ON = Las sirenas se reactivan con cada nueva alarma (ANPI) 

Led Av. Zona 3  
=OFF= No se indica avería comunicaciones.  

=ON = Si se indica avería comunicaciones 

LEDS alarma Z1, Z2, Z2                  
Número de módulos de placas de  relés activas. Se cambian con tecla Z1,  
Llave                                                
Cambia entre las 3 sensibilidades de RBAT
```

**[F4]** `Serie PS` · *10 [SW.DIS] Contacto Normalmente Abierto que indica pérdida de alimentación principal: se conecta al negativo cuando el * · `Serie PS` p.5 · sim 0.80

```
10 [SW.DIS]
Contacto Normalmente Abierto que indica pérdida de
alimentación principal: se conecta al negativo cuando
el LED m se ilumina.
0
0,1 (continuación)

LEDS
DESCRIPCIÓN
M1
M2
OFF indica fallo en el módulo de alimentación N.1
o fallo en el módulo de alimentación N.2.
~
OFF indica fallo en la entrada de alimentación principal de red (230 V~):
- compruebe la presencia de red principal;
- compruebe que el fusible 17 no esté abierto;
- compruebe que el módulo de alimentación esté conectado a la parte electrónica.
_1
_2
_3
OFF indica fallo en la tensión de salida en los terminales [O1], [O2] o [O3] respectivamente:
- si existe el fallo de entrada de alimentación (LED ~ OFF);
- compruebe que la batería esté instalada, conectada y cargada (LEDs A  , a
y s OFF);
-  compruebe que la corriente absorbida por el terminal no excede 1,8A; si es así, v
uelva a ajustar la corriente a los límites establecidos esta se restaurará.
m
ON indica que el módulo de alimentación ha sido desconectado porque la tensión de s
alida se encuentra por encima de límite de seguridad (PS-12 = 15V y en la PS-24 = 34V).
Esta sobretensión puede dañar las baterías y los equipos alimentados de la fuente.
Mientras tanto, la batería garantiza la alimentación a los equipos conectados a la fuente.
Si la tensión de salida vuelve a sus valores normales, por debajo del límite de seguridad,
automáticamente se volverá conectar, en caso contrario, deberá ser reemplazada.
a
ON indica que la batería ha sido desconectada ya que la tensión ha caído por debajo del límite
inferior de seguridad (PS-12 = 9,5V y en la PS-24 = 19V), esto podría dañar la batería de manera
irreversible. La batería se volverá a conectar tan pronto como la fuente puede volver a cargarla.
A
ON indica que la fuente de alimentacón no encuentra la
[… contenido truncado para legibilidad]
```

**[F5]** `FAD-905` · *3.3 Test Inicialización.* · `55393002 Manual Fuentes de Alimentacion FAD-905 ES FR GB IT_V2` p.9 · sim 0.80

```
3.3 Test Inicialización. (continuación)

[TABLA EXTRAÍDA]
3- Funcio | n | a | miento |  |  |  |  |  |  | 
----------------------------------------
3.1 C | a | r | acterís | ticas de | la fuente de | Al | im | ent | aci | ón.
Las Fuentes | de | A | limentaci | ón han sido | diseñadas según la n | or | mativ | a E | N54- | 4 para dar
alimentación | a | uxi | liar a los | sistemas de | control de incendio. |  |  |  |  | 
Las Fuentes | de | A | limentaci | ón han sido | diseñadas para funci | on | ar a | 230 | Vac | y 50/60Hz.
Las dos Fue | nt | es | de Alime | ntación está | n formadas por un m | ód | ulo | de a | lime | ntación de
65W y 150W | d | e | potencia | para las Fue | ntes de 2,5 y 5A resp | ec | tiva | men | te y | un circuito
electrónico d | e | co | ntrol que | supervisa la | Fuente de Alimentac | ión | . |  |  | 
 |  |  |  | 3.2 Rel | é de Avería. |  |  |  |  | 
La Fuente de | A | li | mentación | dispone de | un relé de avería qu | e | nos | per | mite | controlarla
desde un eq | uip | o | remoto. | Con la Fuen | te de Alimentación en | e | stad | o n | orma | l, es decir,
alimentada d | es | de | la red, y | sin avería al | guna, el relé se encu | ent | ra e | nerg | izad | o, si existe
cualquier tip | o d | e | avería el | relé se des | activa de forma inme | dia | ta, | man | dand | o la señal
al equipo rem | o | to. |  |  |  |  |  |  |  | 
Ante una per | di | da | de alime | ntación de re | d 220 Vac, inferior a 2 | m | inut | os, e | l rel | é de avería
no se desact | iv | a, | para evita | r indicacion | es de averías por cort | es | inte | rmit | ente | s de red.
El funcionam | ie | nt | o del Relé | de Avería e | s el siguiente. |  |  |  |  | 
Fuente en fu | nc | io | namiento | sin averías, | en estado normal. |  |  |  |  | 
Entr | e | C | y NA ----
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
La consulta es ambigua porque el síntoma ("alarma de batería baja que no se quita") puede tener causas y procedimientos de diagnóstico muy distintos según el equipo. Antes de responderte con precisión:

**¿Qué equipo o central tienes exactamente?** Necesito fabricante y modelo (por ejemplo: central DXc, fuente FAD-905, fuente Serie PS, fuente TUL500, NFS Supra, u otro).
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

**Razón del judge:** El bot no hace ninguna afirmación técnica concreta, por lo que no hay riesgo de alucinación. La pregunta es genuinamente ambigua: los fragmentos F1-F5 cubren al menos cinco equipos distintos (TUL500, DXc, NFS Supra, Serie PS, FAD-905) con causas y procedimientos de diagnóstico diferentes para la alarma de batería baja, por lo que pedir el modelo exacto es la conducta correcta (ask_clarification). La pregunta formulada es concreta y única, alineada con la conducta esperada.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración indicando que la sintomatología "alarma de batería baja que no se quita aunque las baterías son nuevas" puede corresponder a varias arquitecturas distintas (central convencional, central analógica, fuente de alimentación), y solicitar al menos: (1) fabricante y modelo exacto del equipo que está mostrando la alarma; (2) si la alarma es en una central de incendios, en una fuente independiente, o en una central de intrusión; (3) si se ha medido la resistencia interna de las baterías o solo se han sustituido por baterías "nuevas" sin comprobar; (4) tiempo desde el cambio. Esto es justamente lo que hace el bot.

**Calidad de los chunks:**

- F1 (TUL500): chunk con marca "(continuación)" tras el header — el header repetido es el texto de un punto numerado, no una sección real (patrón: header arbitrario).
- F2 (DXc): el contenido tiene saltos de línea raros dentro de los pasos numerados ("Introducir clave \n + OK. \n"1234"") y rangos numéricos partidos ("200 - 5 \n00 \n mohmios") — patrón de extracción defectuosa de OCR/parsing.
- F5 (FAD-905): [TABLA EXTRAÍDA] aplicado a texto narrativo continuo — falso positivo de detección de tabla.

**Comparación con bot:**

- Sí pidió clarificación correctamente y listó cinco modelos concretos como ejemplos (DXc, FAD-905, Serie PS, TUL500, NFS Supra) extraídos de los propios fragmentos. Es la mejor forma de clarificación posible: específica, accionable y demuestra qué corpus tiene disponible.
- No respondió asumiendo contexto. No hay alucinación.

**Veredicto:**
- [x] **De acuerdo** con el judge
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Caso modélico de ask_clarification. La clarificación es específica (lista modelos), no genérica. Behavior_match=True correctamente.
- **Origen del problema:** N/A (caso correcto).

---

## mc002 — judge dice **PASS ✓** · (2/8)

**Pregunta del técnico:** ¿Cada cuánto hay que hacer mantenimiento?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 1/4 hits · missing: `['tipo', 'componente', 'norma']` · **keyword_pass:** `False`

> _Notas YAML: Pregunta demasiado abierta — puede depender de EN 54, norma local, tipo de equipo._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `unknown` · *5 Mantenimiento* · `MIE-MP-520rv04` p.33 · sim 0.84

```
5 Mantenimiento

5 Mantenimiento

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
Inspección visual de acceso de humedades a los equipos de indicación y control o cualquier 
deterioro. 
5. 
Consulte si algún cambio estructural p
[… contenido truncado para legibilidad]
```

**[F2]** `ZXSe` · *1. Llevar a cabo las rutinas de inspección recomendadas diaria, mensual y trimestralmente.* · `MIE-MI-600` p.43 · sim 0.84

```
1.
Llevar a cabo las rutinas de inspección recomendadas diaria, mensual y trimestralmente.

1.
Llevar a cabo las rutinas de inspección recomendadas diaria, mensual y trimestralmente.

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 41 
5 Mantenimiento 
5.1 Programa de mantenimiento 
• 
La norma EN54-14 recomienda adoptar la siguiente rutina de mantenimiento. 
5.1.1 Inspección diaria  
• 
El usuario debe comprobar lo siguiente: 
1. 
El panel deberá indicar el funcionamiento normal, en caso contrario se deberá registrar la avería e 
indicaciones y enviar a su empresa mantenedora. 
2. 
Cualquier avería deberá ser debidamente atendida 
5.1.2 Inspección mensual 
• 
El usuario debe comprobar lo siguiente: 
1. 
Deberán arrancarse los generadores de reserva y se comprobarán sus niveles de combustible. 
2. 
Al menos un pulsador y detector (de diferentes zonas cada mes) deberán ponerse en alarma y 
comprobar los sistemas conectados de alarma y aviso. 
3. 
Cuando sea posible, deberá activarse cualquier equipo de aviso remoto a bomberos o centro de 
control. 
• 
Cualquier fallo deberá registrarse en el libro de sucesos y tomar las acciones correctivas 
pertinentes cuanto antes. 
5.1.3 Inspección trimestral 
• 
La empresa de mantenimiento deberá comprobar lo siguiente: 
1. 
Revisar los registros de averías y alarmas y el histórico de los paneles y tomar las acciones 
correctivas cuando sean necesarias. 
2. 
Revisar las conexiones de baterías. 
3. 
Revisar las funciones de alarma, avería y auxiliares de los equipos de control e indicación. 
4. 
Inspección visual de acceso de humedades a los equipos de indicación y control o cualquier 
deterioro. 
5. 
Consulte si algún cambio estructural puede afectar al funcionamiento de pulsador
[… contenido truncado para legibilidad]
```

**[F3]** `ZXe` · *1. Llevar a cabo las atenciones recomendadas diaria, mensual y trimestralmente.* · `MIE-MI-530rv001` p.40 · sim 0.84

```
1.
Llevar a cabo las atenciones recomendadas diaria, mensual y trimestralmente.

1.
Llevar a cabo las atenciones recomendadas diaria, mensual y trimestralmente.

MORLEY-IAS 

Paneles de Incendio ZX2e / ZX5e 

Página 40 de 50 
Documento No.MIE-MI-530, Revisión: 001,  
Manual de Instalación 
5 Mantenimiento 
5.1 Tabla de mantenimiento 
En la norma prEN54-14 2002 se recomiendan las siguientes operaciones de mantenimiento que 
deberán realizarse en los intervalos mínimos establecidos. Revise las regulaciones locales para otras 
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
Cuando sea posible cada equipo de aviso remoto a bomberos o centro de control, deberá ser 
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
[… contenido truncado para legibilidad]
```

**[F4]** `ZXSe` · *5.1.3 Inspección trimestral* · `MIE-MI-600` p.43 · sim 0.84

```
5.1.3 Inspección trimestral

5.1.3 Inspección trimestral

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 41 
5 Mantenimiento 
5.1 Programa de mantenimiento 
• 
La norma EN54-14 recomienda adoptar la siguiente rutina de mantenimiento. 
5.1.1 Inspección diaria  
• 
El usuario debe comprobar lo siguiente: 
1. 
El panel deberá indicar el funcionamiento normal, en caso contrario se deberá registrar la avería e 
indicaciones y enviar a su empresa mantenedora. 
2. 
Cualquier avería deberá ser debidamente atendida 
5.1.2 Inspección mensual 
• 
El usuario debe comprobar lo siguiente: 
1. 
Deberán arrancarse los generadores de reserva y se comprobarán sus niveles de combustible. 
2. 
Al menos un pulsador y detector (de diferentes zonas cada mes) deberán ponerse en alarma y 
comprobar los sistemas conectados de alarma y aviso. 
3. 
Cuando sea posible, deberá activarse cualquier equipo de aviso remoto a bomberos o centro de 
control. 
• 
Cualquier fallo deberá registrarse en el libro de sucesos y tomar las acciones correctivas 
pertinentes cuanto antes. 
5.1.3 Inspección trimestral 
• 
La empresa de mantenimiento deberá comprobar lo siguiente: 
1. 
Revisar los registros de averías y alarmas y el histórico de los paneles y tomar las acciones 
correctivas cuando sean necesarias. 
2. 
Revisar las conexiones de baterías. 
3. 
Revisar las funciones de alarma, avería y auxiliares de los equipos de control e indicación. 
4. 
Inspección visual de acceso de humedades a los equipos de indicación y control o cualquier 
deterioro. 
5. 
Consulte si algún cambio estructural puede afectar al funcionamiento de pulsadores, sensores o 
sirenas. Si es así realice una inspección visual. 
• 
Cualquier defecto deberá anotarse en los libros de regis
[… contenido truncado para legibilidad]
```

**[F5]** `ZXSe` · *5.1.4 Inspección anual* · `MIE-MI-600` p.43 · sim 0.84

```
5.1.4 Inspección anual

5.1.4 Inspección anual

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 41 
5 Mantenimiento 
5.1 Programa de mantenimiento 
• 
La norma EN54-14 recomienda adoptar la siguiente rutina de mantenimiento. 
5.1.1 Inspección diaria  
• 
El usuario debe comprobar lo siguiente: 
1. 
El panel deberá indicar el funcionamiento normal, en caso contrario se deberá registrar la avería e 
indicaciones y enviar a su empresa mantenedora. 
2. 
Cualquier avería deberá ser debidamente atendida 
5.1.2 Inspección mensual 
• 
El usuario debe comprobar lo siguiente: 
1. 
Deberán arrancarse los generadores de reserva y se comprobarán sus niveles de combustible. 
2. 
Al menos un pulsador y detector (de diferentes zonas cada mes) deberán ponerse en alarma y 
comprobar los sistemas conectados de alarma y aviso. 
3. 
Cuando sea posible, deberá activarse cualquier equipo de aviso remoto a bomberos o centro de 
control. 
• 
Cualquier fallo deberá registrarse en el libro de sucesos y tomar las acciones correctivas 
pertinentes cuanto antes. 
5.1.3 Inspección trimestral 
• 
La empresa de mantenimiento deberá comprobar lo siguiente: 
1. 
Revisar los registros de averías y alarmas y el histórico de los paneles y tomar las acciones 
correctivas cuando sean necesarias. 
2. 
Revisar las conexiones de baterías. 
3. 
Revisar las funciones de alarma, avería y auxiliares de los equipos de control e indicación. 
4. 
Inspección visual de acceso de humedades a los equipos de indicación y control o cualquier 
deterioro. 
5. 
Consulte si algún cambio estructural puede afectar al funcionamiento de pulsadores, sensores o 
sirenas. Si es así realice una inspección visual. 
• 
Cualquier defecto deberá anotarse en los libros de registro para t
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
¿Qué equipo o sistema estás manteniendo? Los fragmentos que tengo cubren paneles Morley-IAS, pero necesito saber el modelo concreto para darte la información exacta.
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

**Razón del judge:** La pregunta '¿Cada cuánto hay que hacer mantenimiento?' es ambigua porque los fragmentos F1-F5 cubren múltiples productos (Dimension Series, ZXSe, ZXe) con tablas de mantenimiento similares pero distintas fuentes. El bot pide correctamente un detalle concreto (modelo del equipo) antes de responder, lo cual es la conducta esperada 'ask_clarification'. No hace afirmaciones técnicas inventadas y la pregunta de clarificación es pertinente y accionable para el técnico.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración indicando que "mantenimiento" depende de varios ejes: (1) modelo/equipo concreto (las recomendaciones del fabricante varían); (2) si se busca la cadencia regulatoria (EN54-14: atención diaria, mensual, trimestral, anual) o las operaciones específicas para un componente determinado (baterías, detectores, sirenas); (3) si la instalación tiene normativa local más restrictiva. Idealmente, también podría señalar que la norma de referencia es EN54-14 y ofrecer las frecuencias estándar, pidiendo modelo solo para detalles del fabricante.

**Calidad de los chunks:**

- F1, F2, F3 cubren tres manuales Morley-IAS (Dimension Series, ZXSe, ZXe) con tablas EN54-14 prácticamente idénticas — alta redundancia (patrón: duplicación funcional).
- F4 y F5 son secciones de un mismo manual (MIE-MI-600) — solapamiento de contexto.
- Headers de chunks F2 y F3 son simplemente "1. Llevar a cabo las rutinas de inspección..." — fragmentos arbitrarios (patrón: header como bullet de lista, no como sección).

**Comparación con bot:**

- Sí pidió clarificación, pero la respuesta es bastante escueta ("¿Qué equipo o sistema estás manteniendo?"). Podría haber sido más rica: mencionar la norma EN54-14 y los intervalos genéricos (diario/mensual/trimestral/anual) son aplicables transversalmente. Aun así cumple con ask_clarification.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta, aunque la clarificación es algo lacónica. Podría mejorar la helpfulness ofreciendo el marco EN54-14 mientras pide el modelo. No es fallo, pero hay margen.
- **Origen del problema:** N/A.

---

## mc003 — judge dice **PASS ✓** · (3/8)

**Pregunta del técnico:** ¿Cómo se añade un retardo a la sirena?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 1/3 hits · missing: `['fabricante', 'modelo']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *6.2 Retardos* · `MCDT190` p.56 · sim 0.81

```
6.2
Retardos

6.2
Retardos

Matriz de Control
MC-DT-190
       NOTIFIER ESPAÑA
       50
6.2
Retardos
En esta columna puede programar un retardo de hasta
256 segundos entre la entrada de una alarma y la
activación de la salida. Los ajustes de retardo se
redondean al múltiplo de 8 más cercano ; si no se introduce
ningún número significa que la acción de esta línea es
inmediata.
Se pueden programar dos tipos de retardo:
 RETARDOS DE SIRENA (señalados con la letra ‘S’).
 RETARDOS DE CONTROL (señalados con la ‘C’).
Retardo de Sirena: Se utiliza para controlar el
funcionamiento de retardo de las sirenas según se
especifica en EN54-2, párrafo. 7.11, etc. Este tipo de
retardo no se aplica automáticamente, sólo en el caso
de que un operador haya cambiado el panel a modo
‘RETARDO DE SIRENAS (consulte la sección 7.5 Modo
de ‘Sirenas retardadas’ en el Manual de Funcionamiento).
Mientras el temporizador esté funcionando, este retardo
puede anularse pulsando el pulsador ‘FIN RETARDO/
EVACUACIÓN’. Si el modo ‘RETARDO DE SIRENAS’ no
está habilitado, las salidas se activarán de forma
inmediata. Este tipo de retardo deberá utilizarse para todas
las salidas de sirena, a menos que el único objetivo sea
cambiar el modo de aquellas sirenas que ya se han
activado inmediatamente de forma intermitente (mediante
una línea diferente en la Matriz de Control.)
Retardo de Control.  Se utiliza para activar aquellas
salidas que no son sirenas y para cambiar el modo de
una sirena de intermitente (pulsos) a continuo. Este tipo
de retardo se aplica siempre, independientemente del
estado del panel. No se anula mediante la tecla ‘FIN
RETARDO/EVACUACIÓN’ (se puede configurar un
pulsador manual para la función ‘Anular’). No existe
ninguna indicación de la “cuenta atrás” en el panel cuando
este tipo de ret
[… contenido truncado para legibilidad]
```

**[F2]** `ID3000` · *Matriz de Control* · `MCDT190` p.56 · sim 0.80

```
Matriz de Control

Matriz de Control

Matriz de Control
MC-DT-190
       NOTIFIER ESPAÑA
       50
6.2
Retardos
En esta columna puede programar un retardo de hasta
256 segundos entre la entrada de una alarma y la
activación de la salida. Los ajustes de retardo se
redondean al múltiplo de 8 más cercano ; si no se introduce
ningún número significa que la acción de esta línea es
inmediata.
Se pueden programar dos tipos de retardo:
 RETARDOS DE SIRENA (señalados con la letra ‘S’).
 RETARDOS DE CONTROL (señalados con la ‘C’).
Retardo de Sirena: Se utiliza para controlar el
funcionamiento de retardo de las sirenas según se
especifica en EN54-2, párrafo. 7.11, etc. Este tipo de
retardo no se aplica automáticamente, sólo en el caso
de que un operador haya cambiado el panel a modo
‘RETARDO DE SIRENAS (consulte la sección 7.5 Modo
de ‘Sirenas retardadas’ en el Manual de Funcionamiento).
Mientras el temporizador esté funcionando, este retardo
puede anularse pulsando el pulsador ‘FIN RETARDO/
EVACUACIÓN’. Si el modo ‘RETARDO DE SIRENAS’ no
está habilitado, las salidas se activarán de forma
inmediata. Este tipo de retardo deberá utilizarse para todas
las salidas de sirena, a menos que el único objetivo sea
cambiar el modo de aquellas sirenas que ya se han
activado inmediatamente de forma intermitente (mediante
una línea diferente en la Matriz de Control.)
Retardo de Control.  Se utiliza para activar aquellas
salidas que no son sirenas y para cambiar el modo de
una sirena de intermitente (pulsos) a continuo. Este tipo
de retardo se aplica siempre, independientemente del
estado del panel. No se anula mediante la tecla ‘FIN
RETARDO/EVACUACIÓN’ (se puede configurar un
pulsador manual para la función ‘Anular’). No existe
ninguna indicación de la “cuenta atrás” en el panel cuando
este t
[… contenido truncado para legibilidad]
```

**[F3]** `unknown` · *EN54-2:El retardo máximo para la activación de Sirenas de Alarma es de 10m.* · `MIE-MI-580` p.19 · sim 0.81

```
EN54-2:El retardo máximo para la
activación de Sirenas de Alarma es
de 10m.

EN54-2:El retardo máximo para la
activación de Sirenas de Alarma es
de 10m.

– PÁGINA 19 –
MorleyIAS   
Vision LT 

Página 19 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

RETARDO 1 (reconocer alarma)  
Retardo 1: tiempo máximo para pulsar la tecla SILENCIAR 
ZUMBADOR para reconocer una alarma y pasar a Retardo 
2. Si no se pulsa la tecla SILENCIAR ZUMBADOR dentro 
del tiempo de Retardo 1, se activan las sirenas al finalizar 
este tiempo. Es posible configurar 0 seg. (solo se cumple 
retardo secundario) a 300 seg. (5 min.) en pasos de 30 seg. 
Configurar el Retardo primario (R1): 
Seleccionar presionando la Tecla BUZZER =ON 
Cambio cíclico del retardo con tecla RESET 
Indicación del tiempo configurado: 
• Ningún led = 0s solo Retardo 2 (por defecto) 
• Led 1 ON 

= ON = 30 seg.  
• Led 2 Alarm  
= ON = 60 seg. 
• Led 3 Fault 

= ON = 90 seg. 
• Led 4 Disable  

= ON = 120 seg. 
• Led 5 Test  

= ON = 150 seg. 
• Led 6 Earth Fault  

= ON = 180 seg. 
• Led 7 Supply Fault  

= ON = 210 seg. 
• Led 8 System Fault  

= ON = 240 seg. 
• Led 9 Sounders Fault 

= ON = 270 seg. 
• Led 10 Sounders Delayed  
= ON = 300 seg. 

RETARDO 2 (inspección de alarma) 
Retardo 2: tiempo máximo una vez pulsado SILENCIAR 
ZUMBADOR para inspeccionar la causa de la alarma. 
Transcurrido este tiempo (Retardo 2) se activarán las 
salidas de sirenas. Deberá pulsarse la tecla SILENCIAR 
SIRENAS para desactivar el disparo de sirenas. Es posible 
configurar de 0 seg. (solo se cumple retardo primario) a 10 
min.en pasos de 1 min. 
Configurar Retardo secundario (R2): 
Seleccionar presionando la Tecla DELAY ON/OFF=ON 
Cambio cíclico del retardo con tecla
[… contenido truncado para legibilidad]
```

**[F4]** `unknown` · *Seleccionar presionando la Tecla DELAY ON/OFF=ON* · `MIE-MI-580` p.19 · sim 0.80

```
Seleccionar presionando la Tecla DELAY ON/OFF=ON

Seleccionar presionando la Tecla DELAY ON/OFF=ON

– PÁGINA 19 –
MorleyIAS   
Vision LT 

Página 19 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

RETARDO 1 (reconocer alarma)  
Retardo 1: tiempo máximo para pulsar la tecla SILENCIAR 
ZUMBADOR para reconocer una alarma y pasar a Retardo 
2. Si no se pulsa la tecla SILENCIAR ZUMBADOR dentro 
del tiempo de Retardo 1, se activan las sirenas al finalizar 
este tiempo. Es posible configurar 0 seg. (solo se cumple 
retardo secundario) a 300 seg. (5 min.) en pasos de 30 seg. 
Configurar el Retardo primario (R1): 
Seleccionar presionando la Tecla BUZZER =ON 
Cambio cíclico del retardo con tecla RESET 
Indicación del tiempo configurado: 
• Ningún led = 0s solo Retardo 2 (por defecto) 
• Led 1 ON 

= ON = 30 seg.  
• Led 2 Alarm  
= ON = 60 seg. 
• Led 3 Fault 

= ON = 90 seg. 
• Led 4 Disable  

= ON = 120 seg. 
• Led 5 Test  

= ON = 150 seg. 
• Led 6 Earth Fault  

= ON = 180 seg. 
• Led 7 Supply Fault  

= ON = 210 seg. 
• Led 8 System Fault  

= ON = 240 seg. 
• Led 9 Sounders Fault 

= ON = 270 seg. 
• Led 10 Sounders Delayed  
= ON = 300 seg. 

RETARDO 2 (inspección de alarma) 
Retardo 2: tiempo máximo una vez pulsado SILENCIAR 
ZUMBADOR para inspeccionar la causa de la alarma. 
Transcurrido este tiempo (Retardo 2) se activarán las 
salidas de sirenas. Deberá pulsarse la tecla SILENCIAR 
SIRENAS para desactivar el disparo de sirenas. Es posible 
configurar de 0 seg. (solo se cumple retardo primario) a 10 
min.en pasos de 1 min. 
Configurar Retardo secundario (R2): 
Seleccionar presionando la Tecla DELAY ON/OFF=ON 
Cambio cíclico del retardo con tecla RESET 

Indicación del tiempo configurado: 
• Ningún l
[… contenido truncado para legibilidad]
```

**[F5]** `unknown` · *Retardos en salidas* · `MIE-MP-520rv04` p.65 · sim 0.80

```
Retardos en salidas

Serie Dimension Series 
 
MorleyIAS 
 
Manual de Configuración 
Documento No.MIE-MP-520 
Página 65 de 88 
  Activar Modo Horario =  No hay Modo 
  ↕:Cambio                  X:Esc  9:Salv 
 
Presione las teclas ÏÐ para elegir el Modo deseado. La configuración para cada modo se describe en las 
secciones siguientes. 
7.3.9.4.1 
Modo Retardo 
Es posible configurar el panel, para que en determinados momentos, retarde el disparo de alarmas. El panel 
indicará la alarma, pero no activará los programas de salidas hasta finalizar el retardo del Modo Horario 
Retardo. 
 
EN54
!
 
EN54-2  7.11 
Retardos en salidas 
 
 
7.11 c) 10 min. 
Retardo máximo 
para activación de 
salidas de alarma 
El panel puede configurarse para retardar de forma general los 
disparos de alarma.  
Durante el retardo el panel informa de la condición de fuego, pero 
retarda el disparo de los programas de las salidas. El panel activará los 
programas de las salidas, si no se toca en un tiempo configurable. 
Al finalizar el Retardo general, se activarán las salidas siguiendo el 
programa asignado a cada una. Asegúrese de que el retardo de los 
programas y el del Modo Retardo no Superan los 10 min. en total. 
Los Pulsadores (PUL) activan siempre la alarma sin retardo con 
independencia del Modo Retardo. 
Asegúrese de que los Relés (REL y CTL) tienen asignado el programa 
apropiado, ya que éste no se activará hasta finalizado el tiempo del 
Modo Retardo. 
 
Presione las teclas ÏÐ para activar el Modo Retardo. 
 
  Activar Modo Horario =  Retardo 
  ↕:Cambio  ←→:Configurar     X:Esc 9:Salv 
 
Para ajustar los retardos hasta Enterado (Retardo 1) y  Rearme (Retardo 2), presione las teclasÍÎ . El 
display mostrará el Retardo 1 configurado para presionar Enterado. 
 
 
 
Presione las teclas ÏÐ
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
La pregunta menciona "la sirena" sin especificar el equipo. Tengo información de retardos de sirena para dos productos distintos (Notifier ID3000 y Morley-IAS), y el procedimiento es completamente diferente en cada uno.

¿Qué equipo estás usando? ¿Es una central **ID3000**, una **Vision LT** o una **Dimension Series**?
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

**Razón del judge:** La pregunta es genuinamente ambigua: los fragmentos F1/F2 cubren el ID3000 (Notifier, retardo de sirena tipo 'S' en la Matriz de Control) y F3/F4 cubren la Vision LT (MorleyIAS, Retardo 1 y Retardo 2 con teclas físicas), con procedimientos completamente distintos. El bot identifica correctamente esta ambigüedad, nombra los tres productos cubiertos (ID3000, Vision LT, Dimension Series) y pide un único detalle concreto (qué equipo usa el técnico), lo que es exactamente la conducta esperada 'ask_cl

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración porque hay dos arquitecturas radicalmente distintas detrás de "retardo a la sirena": (1) Notifier ID3000 — se programa en la Matriz de Control con un código 'S' y un valor en segundos (hasta 256s, múltiplos de 8), y solo se aplica si el panel está en modo "RETARDO DE SIRENAS"; (2) MorleyIAS Vision LT — se configura con dos retardos físicos (R1 reconocer alarma 0-300s en pasos de 30s; R2 inspección 0-10min en pasos de 1min) usando teclas BUZZER/DELAY ON/OFF y leds; (3) Morley Dimension Series — Modo Horario Retardo con tope EN54-2 de 10 min. El bot debería pedir modelo y, opcionalmente, distinguir entre "retardo general antes de disparo" vs "retardo programable por matriz". Es lo que hace.

**Calidad de los chunks:**

- F1 y F2 son el mismo contenido (MCDT190 p.56) con header diferente — patrón de duplicación.
- F3 y F4 también duplicados (MIE-MI-580 p.19) — el header de F4 es una línea de instrucción suelta ("Seleccionar presionando la Tecla DELAY ON/OFF=ON"), no una sección real (patrón: header arbitrario).
- F5 (Dimension Series) entra como referencia adicional pero solo cubre Modo Horario Retardo.

**Comparación con bot:**

- Sí pidió clarificación, y ofreció tres opciones concretas (ID3000, Vision LT, Dimension Series). Excelente: específica, accionable, ancla en el corpus disponible.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Clarificación de libro: nombra los productos posibles tras detectar la ambigüedad, no pide algo abstracto.
- **Origen del problema:** N/A.

---

## mc004 — judge dice **PASS ✓** · (4/8)

**Pregunta del técnico:** ¿Dónde se conecta el cable de tierra?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 0/2 hits · missing: `['fabricante', 'modelo']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `unknown` · *Asegúrese de que la entrada de tierra está conectada al terminal adecuado.* · `MIEMI120rev05` p.16 · sim 0.78

```
Asegúrese de que la
entrada de tierra está
conectada al terminal
adecuado.

Asegúrese de que la
entrada de tierra está
conectada al terminal
adecuado.

MIE-MI-120
     MORLEY-IAS
            15
5
Cableado
5.1
Instrucciones de cableado
Todo el cableado debe cumplir la norma actual IEE o las
normas de cableado locales aplicables. Observe también
los requisitos de la norma EN54-14 (23007/14) para cableado
e interconexión de un sistema de alarma contra incendio,
así como las partes afectadas del Reglamento de Baja
Tensión (RBT).
Requisito CEM (Compatibilidad Electromagnética): Para
cumplir los requisitos de CEM de las Directivas Europeas,
es necesario utilizar cable apantallado o con revestimiento
metálico.
El tamaño del cable conductor debe ser de 1mm2 como
mínimo. Los terminales aceptan cables flexibles o rígidos
de 1 a 2,5 mm2. Como norma general, se aconseja usar
cable de 1,5 mm2  de sección.
Los cables se deben introducir  en la cabina a través de los
orificios pre-troquelados de 20 mm en la parte superior o
posterior de la caja que sean necesarios.
Alimentación del panel
La alimentación a la central debe estar correctamente
identificada en el cuadro eléctrico con un dispositivo de
conexión de doble polo. La alimentación del panel se
debe conectar a través de diferencial independiente
con elementos de protección (fusible, magnetotérmico...)
de valores adecuados, de acuerdo con las especificaciones.
Asegúrese de que los cables de alimentación se introducen
en la cabina separados de los cables de baja tensión.
Para la debida protección; el panel debe estar conectado a
una toma de Tierra fiable y segura.
Todos los cables de baja tensión tienen un mínimo de 300
Vac.
Pantallas de cable
En caso de instalaciones sometidas a fuertes interferencias,
se aconseja la instalación d
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *Asegúrese de que la entrada de tierra está conectada al terminal adecuado.* · `MIE-MI-580` p.12 · sim 0.76

```
Asegúrese de que la entrada de
tierra está conectada al terminal
adecuado.

Asegúrese de que la entrada de
tierra está conectada al terminal
adecuado.

– PÁGINA 12 –
MorleyIAS   
Vision LT 

Página 12 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

Cableado 
Todo el cableado debe cumplir la norma actual IEE o las normas de cableado locales aplicables. 
Observe también los requisitos de la norma EN54-14 (23007/14) para cableado e interconexión de 
un sistema de alarma contra incendio, así como las partes afectadas del Reglamento de Baja 
Tensión (RBT).  
Requisito CEM (Compatibilidad Electromagnética): Para cumplir los requisitos de CEM de las 
Directivas Europeas, es necesario utilizar cable apantallado o con revestimiento metálico. 
Como norma general, se aconseja usar cable de 1,5 mm2  de sección. 
Los cables se deben introducir  en la cabina a través de los orificios pre-troquelados de 20 mm en 
la parte superior o posterior de la caja que sean necesarios. 
Alimentación del panel 
La alimentación a la central debe estar correctamente identificada en el cuadro eléctrico con un 
dispositivo de conexión de doble polo. La alimentación del panel se debe conectar a través de 
diferencial independiente con elementos de protección (fusible, magnetotérmico...) de valores 
adecuados, de acuerdo con las especificaciones.  
Asegúrese de que los cables de alimentación se introducen en la cabina separados de los cables 
de baja tensión. Conecte los cables de alimentación a los terminales adecuados. 
Para la debida protección; el panel debe estar conectado a una toma de Tierra fiable y segura.  
Todos los cables de baja tensión tienen un mínimo de 300 Vac. 

Pantallas de cable 
En caso de instalaciones sometidas
[… contenido truncado para legibilidad]
```

**[F3]** `unknown` · *Asegúrese de que la entrada de tierra está conectada al terminal adecuado.* · `MIEMI130` p.15 · sim 0.79

```
Asegúrese de que la
entrada de tierra está
conectada al terminal
adecuado.

Asegúrese de que la
entrada de tierra está
conectada al terminal
adecuado.

MIE-MI-130
     MORLEY-IAS
            15
5
Cableado
5.1
Instrucciones de cableado
Todo el cableado debe cumplir la norma actual IEE o las
normas de cableado locales aplicables. Observe también
los requisitos de la norma EN54-14 (23007/14) para cableado
e interconexión de un sistema de alarma contra incendio,
así como las partes afectadas del Reglamento de Baja
Tensión (RBT).
Requisito CEM (Compatibilidad Electromagnética): Para
cumplir los requisitos de CEM de las Directivas Europeas,
es necesario utilizar cable apantallado o con revestimiento
metálico.
El tamaño del cable conductor debe ser de 1mm2 como
mínimo. Los terminales aceptan cables flexibles o rígidos
de 1 a 2,5 mm2. Como norma general, se aconseja usar
cable de 1,5 mm2  de sección.
Los cables se deben introducir  en la cabina a través de los
orificios pre-troquelados de 20 mm en la parte superior o
posterior de la caja que sean necesarios.
Alimentación del panel
La alimentación a la central debe estar correctamente
identificada en el cuadro eléctrico con un dispositivo de
conexión de doble polo. La alimentación del panel se
debe conectar a través de diferencial independiente
con elementos de protección (fusible, magnetotérmico...)
de valores adecuados, de acuerdo con las especificaciones.
Asegúrese de que los cables de alimentación se introducen
en la cabina separados de los cables de baja tensión.
Para la debida protección; el panel debe estar conectado a
una toma de Tierra fiable y segura.
Todos los cables de baja tensión tienen un mínimo de 300
Vac.
Pantallas de cable
En caso de instalaciones sometidas a fuertes interferencias,
se aconseja la instalación d
[… contenido truncado para legibilidad]
```

**[F4]** `ID50/60` · *Nota:Todas las conexiones a tierra incorporan una lengüeta de cierre. Para extraer esta conexión, estire de la lengüeta * · `MIDT156` p.25 · sim 0.80

```
Nota:Todas las conexiones a tierra incorporan una
lengüeta de cierre. Para extraer esta conexión, estire de
la lengüeta (1) NO del cable de conexión a tierra (2).

Nota:Todas las conexiones a tierra incorporan una
lengüeta de cierre. Para extraer esta conexión, estire de
la lengüeta (1) NO del cable de conexión a tierra (2).

Cableado
Centrales ID50/60 - Manual de instalación, puesta en marcha y configuración
MI-DT-156_C
     19
3
Cableado
3.1
Instrucciones de cableado
Todo el cableado debe cumplir la norma actual IEE
(BS7671) o las normas de cableado locales aplicables.
Observe también los requisitos de la norma EN54-14 para
cableado e interconexión de un sistema de alarma contra
incendio.
Si desea información sobre las entradas y salidas del
cableado, consulte las instrucciones de cableado
apropiadas para identificar los terminales. Véase el
capítulo sobre puesta en marcha, la sección 4.4:
Comprobaciones del cableado externo.
Siga estas instrucciones para realizar la conexión de los
cables:
1
Introduzca los cables en la cabina por los troqueles
de 20 mm situados en la parte superior de la caja
posterior. Asegúrese que todas las aberturas en la
caja posterior están cerradas antes de conectar la
alimentación al panel. Por ejemplo, si se han
agujereado más troqueles de los necesarios, debe
taparlos para evitar el acceso a tensiones de riesgo.
2
Los extremos de los cables deben ser suficientemente
largos para poder conectar fácilmente los puntos de
terminación en la puesta en marcha.
3
Los cables deben ser apantallados y terminados con
prensaestopas de forma que cumplan las normas
locales de cableado y así mantener la integridad de
la conexión de la pantalla. La pantalla del cable queda
sujeta en el interior del prensaestopas, necesario para
que se forme una unión de 360º
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *Nota:Todas las conexiones a tierra incorporan una lengüeta de cierre. Para extraer esta conexión, estire del conector, N* · `MIDT190` p.20 · sim 0.80

```
Nota:Todas las conexiones a tierra incorporan una
lengüeta de cierre. Para extraer esta conexión,
estire del conector, NO del cable de tierra.

Nota:Todas las conexiones a tierra incorporan una
lengüeta de cierre. Para extraer esta conexión,
estire del conector, NO del cable de tierra.

Panel ID3000 - Manual de instalación y puesta en marcha
Instalación - Cableado
MI-DT-190_D
       14
3
Cableado
3.1
Instrucciones de cableado
Todo el cableado debe cumplir la norma actual IEE
(BS7671) o las normas de cableado locales aplicables.
Observe también los requisitos de la norma EN54-14 para
cableado e interconexión de un sistema de alarmas contra
incendio.
Si desea información sobre las entradas y salidas del
cableado, consulte las instrucciones de cableado
apropiadas para identificar los terminales. Véase el
capítulo 7 de Puesta en marcha, la Sección 7.4:
Cableado externo.
Siga estas instrucciones para realizar la conexión de los
cables:
1
Introduzca los cables en la cabina por los troqueles
de 20 mm situados en la parte superior de la caja
posterior. Asegúrese de que todas las aberturas en la
caja posterior están cerradas antes de conectar la
alimentación al panel. Por ejemplo, si se han
agujereado más troqueles de los necesarios, debe
taparlos para evitar el acceso a tensiones de riesgo.
2
Los extremos de los cables deben ser suficientemente
largos para poder conectar fácilmente los puntos de
terminación en la puesta en marcha.
3
Los cables deben ser apantallados y terminados con
prensaestopas de forma que cumplan las normas
locales de cableado y así mantener la integridad de
la conexión de la pantalla. La pantalla del cable queda
sujeta en el interior del prensaestopas, necesario para
que se forme una unión de 360º con el metal de la
caja posterior.
4
La alimentación al pan
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
La pregunta es ambigua porque los fragmentos recuperados corresponden a varios productos distintos (Morley-IAS y Notifier). Para darte la ubicación exacta del terminal de tierra, ¿qué equipo concreto estás instalando?
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

**Razón del judge:** La pregunta '¿Dónde se conecta el cable de tierra?' es genuinamente ambigua: los fragmentos F1-F5 cubren al menos cinco productos distintos (MIE-MI-120, MIE-MI-580, MIE-MI-130, ID50/60, ID3000), cada uno con instrucciones de tierra ligeramente diferentes (espárrago M4, terminal adecuado, lengüeta de cierre, lateral interno de la tapa según V7). El bot identifica correctamente la ambigüedad y pide un único detalle concreto (qué equipo se está instalando), lo que es la conducta esperada 'ask_clari

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración indicando que el "terminal de tierra" varía físicamente entre equipos. Si quiere ser más útil podría ofrecer una pauta común: (a) la entrada de tierra de red se conecta al espárrago/terminal de tierra de la caja; (b) las pantallas de los lazos se conectan en un único punto (típicamente al chasis); (c) en algunos modelos los conectores de tierra tienen lengüeta de cierre — extraer tirando de la lengüeta NO del cable. Pero por la variedad de productos (Morley-IAS MIE-MI-120/130/580, Notifier ID50/60, ID3000) es razonable pedir el equipo concreto, que es lo que hace el bot.

**Calidad de los chunks:**

- F1, F2, F3 son chunks casi idénticos en tres manuales Morley-IAS distintos (MIE-MI-120, MIE-MI-580, MIE-MI-130) con el mismo header "Asegúrese de que la entrada de tierra está conectada al terminal adecuado." — patrón de duplicación cruzada entre manuales (texto reciclado).
- El header en cada caso es una nota/instrucción concreta, no una sección del manual — patrón de header arbitrario.

**Comparación con bot:**

- Sí pidió clarificación, aunque relativamente breve. Mencionó los dos fabricantes (Morley-IAS, Notifier) presentes en el corpus. Podría haber listado los modelos concretos.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta. Margen menor de mejora en helpfulness (citar los modelos concretos, no solo los fabricantes).
- **Origen del problema:** N/A.

---

## mc005 — judge dice **PASS ✓** · (5/8)

**Pregunta del técnico:** ¿Mi detector antiguo vale para la nueva central?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 3/4 hits · missing: `['cuál']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Las nuevas tarjetas de multimódulos de System Sensor SC-6, CZ-6, IM-10 y CR-6 NO son compatibles con centrales ID1000 an* · `TIDT066_copia` p.1 · sim 0.80

```
Las nuevas tarjetas de multimódulos de System Sensor SC-6, CZ-6, IM-10 y CR-6
NO son compatibles con centrales ID1000 antiguas que tengan tarjetas de lazo con
versión de software 15.3 y 16.5.

Toda la información contenida en este documento puede ser modificada sin previo aviso
Información
Técnica
TI-DT-066
22/05/03
1 de 1
INCOMPATIBILIDAD DE LOS MÓDULOS SC-6,
CZ-6, IM-10 Y CR-6 EN LA CENTRAL ID1000 CON
TARJETAS DE LAZO CON SOFTWARE 15.3 ó 16.5
Las nuevas tarjetas de multimódulos de System Sensor SC-6, CZ-6, IM-10 y CR-6
NO son compatibles con centrales ID1000 antiguas que tengan tarjetas de lazo con
versión de software 15.3 y 16.5.
Las centrales ID1000 con versión de lazo 18.3 suministradas desde el año 2.000 SÍ
son compatibles con estas nuevas tarjetas.
Las tarjetas SC-6, CZ-6, IM-10 y CR-6 son totalmente compatibles con el resto de
centrales de Notifier ID200, AFP200, AFP1010/AM2020, AM2000, AM6000, ID50,
ID3000 y AFP4000.


[TABLA EXTRAÍDA]
|  |  |  |  |  | TI-DT-066 |  |  | 22/05/03
----------------------------------------
INC | OMPA | TIB | IL | IDA | D DE | LOS M | ÓDU | LO | S SC-6
CZ-6 | , IM-10 | Y | CR | -6 E | N LA | CENT | RAL I | D1 | 000 C
TARJ | ETAS | DE | L | AZO | CON | SOFT | WARE | 1 | 5.3 ó 1
Las nuev | as tarjetas | de m | ulti | módul | os de Sys | tem Senso | r SC-6, | CZ- | 6, IM-10 y
NO son c | ompatibles | con | cen | trales | ID1000 a | ntiguas qu | e tengan | tarje | tas de laz
versión d | e software | 15.3 | y 1 | 6.5. |  |  |  |  | 
Las centr | ales ID100 | 0 con | ve | rsión d | e lazo 18 | .3 suminist | radas d | esde | el año 2.0
son comp | atibles con | esta | s n | uevas | tarjetas. |  |  |  | 
Las tarjet | as SC-6, C | Z-6, | IM- | 10 y C | R-6 son | totalmente | compat | ibles | con el res
centrales | de Notifier | ID2 | 00, | AFP2
[… contenido truncado para legibilidad]
```

**[F2]** `INSPIRE` · *La búsqueda de un dispositivo de alta potencia # se identificarán como dispositivos antiguos de no alta potencia.* · `HOP-138-8ES  issue 6_01-2026_Co` p.17 · sim 0.80

```
La búsqueda de un dispositivo de alta potencia # se
identificarán como dispositivos antiguos de no alta
potencia.

La búsqueda de un dispositivo de alta potencia # se
identificarán como dispositivos antiguos de no alta
potencia.

17
INPIRE E10/E15 Centrales de alarmas de detección de incendios – Instrucciones de puesta en marcha
 Las averías en un lazo leído pueden deberse a las condiciones que se indican a continuación:
- Discordancia entre el diseño de la instalación y el cableado.
- Averías en el cableado
- Condiciones externas, es decir, la presencia de una fuente de RFI fuerte que afecta de forma perjudicial a la central.
- Error de un módulo o de una Fuente de alimentación (FA).
- Conexionado incorrecto en los dispositivos
03	 Lea los mensajes de avería y tome las medidas necesarias para rectificar los problemas en el lazo, consulte también "Mensajes y 
sus significados". Seleccione Hecho al completar. Si no hay averías, vuelva <- a la página Información del sistema.
04	 Repita los pasos 01 a 03 si se han rectificados las averías de lazo.
05	 Repita los pasos 01 a 04 y Auto Configuración de búsqueda del siguiente lazo hasta que se descubran todos los lazos. 
Averías y soluciones típicas
Avería
Solución
Se reviso la avería de circuito abierto en lazo pero la 
central sigue mostrando una avería.
Si pulsa el botón REARMAR, podrá limpiarse la avería de tipo 
enclavado.
Dos dispositivos del lazo tienen la misma dirección, 
pero en la central no se ha indicado ningún problema. 
Localice los dispositivos con LED amarillos intermitentes. Estos 
son los dispositivos que tienen la misma dirección. Revise el 
dispositivo y corrija los conflictos de dirección. Consulte con 
los planos tal como se instalaron para determinar la dirección 
correcta.
Dispositivo configurado con l
[… contenido truncado para legibilidad]
```

**[F3]** `INSPIRE` · *La búsqueda de un dispositivo de alta potencia # se identificarán como dispositivos antiguos de no alta potencia.* · `HOP-138-8ES  issue 6_01-2026_Co` p.17 · sim 0.80

```
La búsqueda de un dispositivo de alta potencia # se
identificarán como dispositivos antiguos de no alta
potencia. (continuación)

[TABLA EXTRAÍDA]
P | rog | ra | ma | d | e Co | n | fi |  | g | u |  | rac | ión de | CLSS | 
----------------------------------------
Es i | mportante | anotar la | contraseña | de i | nicio de sesi | ón y | el có | di | go | de | a | cceso util | izados para el program | a de configuración de | CLSS,
por | tal de CLSS | Cloud y s | on los mism | os | para la aplic | ació | n CL | SS. |  |  |  |  |  |  | 
El p | rograma es | accesible | a los usua | rios | registrados | a tra | vés d | e | un | siti | o | web: http | s://hwll.co/HOP-431-1 | 00 | 
01 | Descargue | el progra | ma de confi | gura | ción CLSS c | om | primi | do | y g | uá | rd | elo en el | portátil. |  | 
02 | Haga dobl | e clic en el | archivo co | mpri | mido y siga | las i | nstru | cci | on | es | q | ue se indi | can en la pantalla para | instalar el software, | 
 | necesitará | derechos | de administ | rad | or para insta | lar e | l pro | gra | m | a. |  |  |  |  | 
03 | Conecte su | portátil a | Internet y c | om | pruebe para | ase | gurar | se | de | qu | e | la VPN es | té desconectada. |  | 
04 | Abra el pro | grama e in | icie sesión | con | los datos de | inic | io de | se | si | ón d | e | su cuen | ta CLSS (name@honey | wellcloud.com) y la co | ntrase
 | del código | de acceso | . |  |  |  |  |  |  |  |  |  |  |  | 
 | Nota: Si no p | uede inicia | r sesión en el | pro | grama, vaya a | la co | nfigur | ac | ión | del | c | ortafuego | s > aplicaciones y caracterí | sticas permitidas > Hag | a clic en
 | las casillas d | e verificaci | ón para la he | rram | ienta de confi | gura | ción d | e C | LS | S y | H | oneywell.F | TS.WebAPI.Server. Reinici | e el port
[… contenido truncado para legibilidad]
```

**[F4]** `TBUD-150` · *1- Introducción 1- Introduction* · `55315012 Manual Tarjeta de bucle TBUD-150 Instalacion ES FR GB IT` p.1 · sim 0.80

```
1- Introducción
1- Introduction

1- Introducción
1- Introduction

ESPAÑOL
TARJETA BUCLE CENTRAL ANALÓGICA
1- Introducción
1- Introduction
Estas tarjetas han sido diseñadas para añadir dos 
bucles a la central analógica de 4 bucle ampliable a 8. 
Esta tarjeta permite añadir dos bucles por tarjeta a la 
Central Analógica.
Las centrales analógicas pueden alojar hasta dos 
tarjetas de bucle, obteniendo así un total de 8 bucles 
analógicos. De fábrica la central analógica de 4 bucles 
ampliable a 8 viene dotada de 4 bucles, es necesario 
añadir dos tarjetas para conseguir 8 bucles.
Tarjeta de Expansión de 2 bucles analógicos
Esta tarjeta proporciona dos bucles analógicos.
This card provides two analogue loops.
La instalación del bucle debe ser cerrada, es decir, el 
cable de dos hilos apantallado debe salir de la central 
y volver a ella, en este cable conectaremos todos los 
dispositivos del sistema.
El cable que debemos utilizar debe ser como mínimo 
de 1,5 mm2 de diámetro, trenzado  y se debe utilizar 
apantallado para evitar interferencias.
The facility should be closed loop, ie the two-wire 
shielded cable should come out of the panel and 
return to it, this cable will connect all devices in the 
system.
The cable used must be at least 1.5 mm2, braided 
shield should be used to avoid interference. The 
maximum length of the loop cable is 2 km. 
La longitud máxima del lazo es de 2 Km. La resistencia 
del cable del bucle debe ser inferior a 44 Ohm y la 
capacidad máxima de la línea debe ser inferior a 500 
nF.
Conecte los hilos de salida en el punto de la regleta 
indicada con S+, S- y la pantalla al borne indicado como 
, y el retorno del bucle en el punto de la regleta indicada 
con R+ y R- y la pantalla del retorno al borne indicado 
como Tierra.
En cada una de las con
[… contenido truncado para legibilidad]
```

**[F5]** `INSPIRE` · *La búsqueda de un dispositivo de alta potencia # se identificarán como dispositivos antiguos de no alta potencia.* · `HOP-138-8ES  issue 6_01-2026_Co` p.17 · sim 0.80

```
La búsqueda de un dispositivo de alta potencia # se
identificarán como dispositivos antiguos de no alta
potencia. (continuación)

[TABLA EXTRAÍDA]
|  | INPIR | E E | 10/E | 15 Centrale | s de alarma | s de detecció | n de in | cendios – Instru | cciones de | puesta e | n march
----------------------------------------
 |  | Las averías e | n u | n lazo | leído pueden | deberse a la | s condiciones | que se | indican a contin | uación: |  | 
 |  | - Discordanci | a en | tre el | diseño de la | instalación y | el cableado. |  |  |  |  | 
 |  | - Averías en e | l ca | blead | o |  |  |  |  |  |  | 
 |  | - Condicione | s ext | ernas | , es decir, la | presencia de | una fuente de | RFI fue | rte que afecta de | forma perju | dicial a la | central.
 |  | - Error de un | mód | ulo o | de una Fuen | te de alimen | tación (FA). |  |  |  |  | 
 |  | - Conexionad | o in | corre | cto en los dis | positivos |  |  |  |  |  | 
03 Lea los | men | sajes de aver | ía y | tome | las medidas | necesarias p | ara rectificar lo | s probl | emas en el lazo, c | onsulte tam | bién "Men | sajes y
sus sig | nific | ados". Selecci | one | Hech | o al complet | ar. Si no hay | averías, vuelva | <- a la | página Informació | n del sistem | a. | 
04 Repita | los p | asos 01 a 03 | si s | e han | rectificados l | as averías de | lazo. |  |  |  |  | 
05 Repita | los p | asos 01 a 04 | y Au | to Co | nfiguración | de búsqueda | del siguiente | lazo ha | sta que se descu | bran todos | los lazos. | 
Averías | y so | luciones tí | pic | as |  |  |  |  |  |  |  | 
Avería |  |  |  |  |  |  | Solución |  |  |  |  | 
Se reviso | la a | vería de circ | uito | abier | to en lazo p | ero la | Si pulsa el bo | tón RE | ARMAR, podrá l | impiarse la | avería de | tipo
central s | igue | mostrando | una | averí |
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, necesito que me indiques:

1. **¿Qué detector tienes exactamente?** (modelo completo, incluyendo sufijo)
2. **¿A qué central nueva lo quieres conectar?** (fabricante y modelo)

La compatibilidad entre detector y central depende del protocolo de lazo, el fabricante y la versión de software de cada equipo — no puedo darte una respuesta fiable sin esos datos.
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

**Razón del judge:** La pregunta '¿Mi detector antiguo vale para la nueva central?' es completamente ambigua: no especifica modelo de detector ni modelo de central. El bot no hace afirmaciones técnicas concretas (no hay nada que verificar contra el corpus), sino que pide exactamente los dos datos mínimos necesarios (modelo de detector y modelo de central nueva) para poder responder, lo cual es la conducta esperada 'ask_clarification'. La respuesta es relevante, honesta y accionable para el técnico.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración: (1) modelo concreto del detector (referencia exacta del fabricante con sufijo); (2) modelo concreto de la "nueva central" (fabricante + modelo + versión de software del lazo si se sabe). La compatibilidad detector–central depende del protocolo de lazo (CLIP, OPAL, Apollo, Hochiki, etc.), la versión de software de la tarjeta de lazo (ej.: F1 documenta que ID1000 con SW 15.3/16.5 NO acepta SC-6/CZ-6/IM-10/CR-6, pero SW 18.3 sí), y la consideración de si el detector tiene "alta potencia" vs "antiguo de no alta potencia" en sistemas tipo INSPIRE E10/E15. Sin esos dos datos no se puede responder con honestidad.

**Calidad de los chunks:**

- F2, F3 y F5 son todos del mismo manual (HOP-138-8ES p.17), uno como chunk y otros dos como "(continuación)" — patrón claro de duplicación con [TABLA EXTRAÍDA] mal aplicado en F3 y F5 (la "tabla" extraída es un párrafo de texto fragmentado en columnas).
- F4 (TBUD-150) trae datos relevantes (longitud máxima del lazo 2 km, resistencia <44 Ω, capacidad <500 nF) pero no es lo que se pregunta — ruido en el retrieval.
- F1 es una nota técnica antigua (TI-DT-066, 22/05/03) muy específica sobre incompatibilidad ID1000 — útil pero no exhaustiva.

**Comparación con bot:**

- Sí pidió clarificación correctamente, listando los dos datos mínimos (modelo del detector + modelo de la central). Respuesta limpia y honesta.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Behavior_match=True correctamente. Buen ejemplo de ask_clarification por dos ejes (detector y central).
- **Origen del problema:** N/A.

---

## mc006 — judge dice **FAIL ✗** · (6/8)

**Pregunta del técnico:** ¿Cuál es la distancia máxima de cableado?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 3/4 hits · missing: `['central']` · **keyword_pass:** `False`
> 🐛 BUG candidato: observed==expected pero el judge dice behavior_match=False

### Fragmentos que el bot usó (top 5)

**[F1]** `unknown` · *Cableado* · `MIE-MI-580` p.12 · sim 0.72

```
Cableado

Cableado

– PÁGINA 12 –
MorleyIAS   
Vision LT 

Página 12 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

Cableado 
Todo el cableado debe cumplir la norma actual IEE o las normas de cableado locales aplicables. 
Observe también los requisitos de la norma EN54-14 (23007/14) para cableado e interconexión de 
un sistema de alarma contra incendio, así como las partes afectadas del Reglamento de Baja 
Tensión (RBT).  
Requisito CEM (Compatibilidad Electromagnética): Para cumplir los requisitos de CEM de las 
Directivas Europeas, es necesario utilizar cable apantallado o con revestimiento metálico. 
Como norma general, se aconseja usar cable de 1,5 mm2  de sección. 
Los cables se deben introducir  en la cabina a través de los orificios pre-troquelados de 20 mm en 
la parte superior o posterior de la caja que sean necesarios. 
Alimentación del panel 
La alimentación a la central debe estar correctamente identificada en el cuadro eléctrico con un 
dispositivo de conexión de doble polo. La alimentación del panel se debe conectar a través de 
diferencial independiente con elementos de protección (fusible, magnetotérmico...) de valores 
adecuados, de acuerdo con las especificaciones.  
Asegúrese de que los cables de alimentación se introducen en la cabina separados de los cables 
de baja tensión. Conecte los cables de alimentación a los terminales adecuados. 
Para la debida protección; el panel debe estar conectado a una toma de Tierra fiable y segura.  
Todos los cables de baja tensión tienen un mínimo de 300 Vac. 

Pantallas de cable 
En caso de instalaciones sometidas a fuertes interferencias, se aconseja la instalación de ferritas 
(A) utilice abrazaderas (B) en el cableado y cables apantallados
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *Como norma general, se aconseja usar cable de 1,5 mm2 de sección.* · `MIE-MI-580` p.12 · sim 0.73

```
Como norma general, se aconseja usar cable de 1,5 mm2 de sección.

Como norma general, se aconseja usar cable de 1,5 mm2 de sección.

– PÁGINA 12 –
MorleyIAS   
Vision LT 

Página 12 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

Cableado 
Todo el cableado debe cumplir la norma actual IEE o las normas de cableado locales aplicables. 
Observe también los requisitos de la norma EN54-14 (23007/14) para cableado e interconexión de 
un sistema de alarma contra incendio, así como las partes afectadas del Reglamento de Baja 
Tensión (RBT).  
Requisito CEM (Compatibilidad Electromagnética): Para cumplir los requisitos de CEM de las 
Directivas Europeas, es necesario utilizar cable apantallado o con revestimiento metálico. 
Como norma general, se aconseja usar cable de 1,5 mm2  de sección. 
Los cables se deben introducir  en la cabina a través de los orificios pre-troquelados de 20 mm en 
la parte superior o posterior de la caja que sean necesarios. 
Alimentación del panel 
La alimentación a la central debe estar correctamente identificada en el cuadro eléctrico con un 
dispositivo de conexión de doble polo. La alimentación del panel se debe conectar a través de 
diferencial independiente con elementos de protección (fusible, magnetotérmico...) de valores 
adecuados, de acuerdo con las especificaciones.  
Asegúrese de que los cables de alimentación se introducen en la cabina separados de los cables 
de baja tensión. Conecte los cables de alimentación a los terminales adecuados. 
Para la debida protección; el panel debe estar conectado a una toma de Tierra fiable y segura.  
Todos los cables de baja tensión tienen un mínimo de 300 Vac. 

Pantallas de cable 
En caso de instalaciones sometidas a fuertes interfe
[… contenido truncado para legibilidad]
```

**[F3]** `unknown` · *Cableado de señalización y control* · `MIE-MI-580` p.12 · sim 0.72

```
Cableado de señalización y control

Cableado de señalización y control

– PÁGINA 12 –
MorleyIAS   
Vision LT 

Página 12 de 28                     Doc. No-MIE-MI-580                   Manual de Instalación, configuración y Funcionamiento 

Cableado 
Todo el cableado debe cumplir la norma actual IEE o las normas de cableado locales aplicables. 
Observe también los requisitos de la norma EN54-14 (23007/14) para cableado e interconexión de 
un sistema de alarma contra incendio, así como las partes afectadas del Reglamento de Baja 
Tensión (RBT).  
Requisito CEM (Compatibilidad Electromagnética): Para cumplir los requisitos de CEM de las 
Directivas Europeas, es necesario utilizar cable apantallado o con revestimiento metálico. 
Como norma general, se aconseja usar cable de 1,5 mm2  de sección. 
Los cables se deben introducir  en la cabina a través de los orificios pre-troquelados de 20 mm en 
la parte superior o posterior de la caja que sean necesarios. 
Alimentación del panel 
La alimentación a la central debe estar correctamente identificada en el cuadro eléctrico con un 
dispositivo de conexión de doble polo. La alimentación del panel se debe conectar a través de 
diferencial independiente con elementos de protección (fusible, magnetotérmico...) de valores 
adecuados, de acuerdo con las especificaciones.  
Asegúrese de que los cables de alimentación se introducen en la cabina separados de los cables 
de baja tensión. Conecte los cables de alimentación a los terminales adecuados. 
Para la debida protección; el panel debe estar conectado a una toma de Tierra fiable y segura.  
Todos los cables de baja tensión tienen un mínimo de 300 Vac. 

Pantallas de cable 
En caso de instalaciones sometidas a fuertes interferencias, se aconseja la instalación de ferritas 
(A) utilice a
[… contenido truncado para legibilidad]
```

**[F4]** `ZXSe` · *6.3 Cables recomendados* · `MIE-MI-600` p.50 · sim 0.72

```
6.3 Cables recomendados

6.3 Cables recomendados

Paneles de Incendio de la Serie ZX 

MORLEY-IAS 

Manual de instalación 
Documento: MIE-MI-600 
Página 48 
6.3 Cables recomendados 
• 
Todos los cables conectados a los paneles de la Serie ZX, deben ser cables resistentes al 
fuego. El cable de conexión a tierra debe conectarse a a tierra en un terminal de tierra de la 
cabina o en el prensaestopas de entrada de cable y el panel debe conectarse a un punto de 
tierra adecuado. 

Revise las regulaciones locales y reglamentos para asegurar el cumplimiento del cableado, según 
los requerimientos de los mismos.  
En la EN54-14, se establecen los criterios de instalación para los sistemas de protección contra 
incendios. 
 ‘d) Los cables resistentes al fuego estándar deben cumplir con la clasificación PH30 cuando se 
prueban según EN 50200 y mantener la integridad del circuito si se exponen a la siguiente prueba:  
- Una muestra de cable se expone, de forma simultánea, a una llama con una temperatura de 
830ºC – 0+40ºC y a un choque mecánico durante unos 15 minutos; seguidos de una exposición 
simultánea a un spray de agua y choque mecánico durante 15 minutos más. 
e) Los cables resistentes al fuego mejorados deben cumplir con la clasificación PH120 cuando 
se prueban según  EN50200 y mantener la integridad del circuito si se exponen a la siguiente 
prueba: 
- Una muestra de cable se expone, de forma simultánea, a una llama con una temperatura de 
930ºC – 0+40ºC y a un choque mecánico durante unos 60 minutos; seguidos de una exposición 
simultánea a un spray de agua y choque mecánico durante 60 minutos más.’ 

Cable del lazo 
Un cable de lazo transmite datos por lo que su elección es importante. Obsérvese lo siguiente:  
- 
En países donde es obligatoria la directiva europea E
[… contenido truncado para legibilidad]
```

**[F5]** `ZXe` · *3.4.13 Cables recomendados* · `MIE-MI-530rv001` p.29 · sim 0.72

```
3.4.13 Cables recomendados

3.4.13 Cables recomendados

Paneles de Incendio ZX2e / ZX5e 

MORLEY-IAS 

Manual de Instalación 
Documento No.MIE-MI-530, Revisión:001,  
Página 29 de 50 
3.4.13 Cables recomendados 

Todos los cables conectados al los paneles ZX2e y ZX5e, deberían ser cables resistentes al 
fuego de par trenzado y apantallado. La conexión de drenaje de las pantallas, deberá 
conectarse en un solo punto al conector específico o al chasis. 
Revise las regulaciones locales y reglamentos para asegurar el cumplimiento del cableado, 
según los requerimientos de los mismos.  
A continuación se describen los cables recomendados para cada uso: 
• 
Cableado de Lazo analógico (Alimentación y señal de equipos analógicos) al menos será: 

Cable de par trenzado y apantallado 

10/20 vueltas por metro mínimo 
Conductor de cobre pulido flexible clase1 
Aislamiento de espesor nominal del aislamiento 0,7 no propagador de la llama y baja emisión de 
humos 
Pantalla laminar de aluminio con drenaje de cobre estañado rígido de 0,50 mm2. 
Resistencia eléctrica del conductor a 20 ºC (Ω/Km) 13,1 
Resistencia eléctrica del aislamiento a 20 ºC  (Ω/Km) ≥ 20 
Capacidad entre conductores máxima total 0,5 μF 
Impedancia máxima total 40Ω 

• 
Cableado de Sirenas y control de incendio: 

El cableado de señalización y aviso, así como aquellos sistemas que están vinculados con la 
evacuación y control de incendio del edificio o la interconexión de sistemas de detección de incendio, deberán 
garantizar su servicio para asegurar la evacuación y se estipula que deberán ser resistentes al fuego. 
• 
Cableado de comunicaciones RS-485: 

El cableado de comunicaciones RS-485 deberá ser trenzado y apantallado con impedancia 
característica de 120Ω. 
Todo el cableado de señalización y control, deberá
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
La pregunta no especifica el equipo ni el tipo de circuito. Los fragmentos recuperados cubren dos productos distintos de Morley-IAS, con datos diferentes según el circuito. Aquí tienes lo que sí está documentado:

---

**MorleyIAS Vision LT (MIE-MI-580):**
El manual **no especifica una distancia máxima de cableado** para ningún circuito [F1][F2][F3]. Solo indica que se recomienda cable de **1,5 mm²** de sección [F1].

---

**MorleyIAS Serie ZX (ZXSe / ZX2e / ZX5e):**

**Cable de lazo analógico:**
- Longitud máxima del lazo: **1,5 km** (incluyendo lazo principal y ramales) [F4]
- Sección mínima: **1,5 mm²** [F4]
- Impedancia máxima total: **40 Ω** [F5]
- Capacidad entre conductores máxima total: **0,5 μF** [F5]

**Cable RS-485:**
- El manual no especifica longitud máxima para este circuito [F5].

**Cable de sirenas/control:**
- El manual no especifica longitud máxima para este circuito [F4][F5].

---

¿Qué modelo concreto estás instalando y para qué circuito necesitas la distancia máxima (lazo, sirenas, RS-485, alimentación)?

**Fuentes:** MIE-MI-580 (sin revisión registrada); MIE-MI-600 (sin revisión registrada); MIE-MI-530rv001 (Revisión 001)
```

### Veredicto del judge: **FAIL ✗**

```
- citation_faithful: True
- corpus_faithful:   True
- miscitation:       False
- relevant:          True
- helpful:           True
- honest:            True
- behavior_match:    False
```

**Razón del judge:** El bot respondió con datos técnicos correctos y bien citados (1,5 km de lazo en F4, 40 Ω e impedancia en F5, sección 1,5 mm² en F4/F5), todos verificables en los fragmentos F. Sin embargo, la conducta esperada era 'ask_clarification' — la pregunta '¿Cuál es la distancia máxima de cableado?' es ambigua (no especifica producto ni tipo de circuito) y el bot debía pedir UN detalle concreto antes de responder. En cambio, el bot respondió directamente con múltiples productos y circuitos, y solo al fin

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

Caso de ambigüedad doble: (1) qué equipo y (2) qué tipo de circuito (lazo analógico, RS-485, sirenas, alimentación). La respuesta ideal sería pedir aclaración indicando ambos ejes: "¿Para qué equipo y para qué tipo de circuito? La distancia máxima depende fuertemente de ambos — un lazo analógico Morley ZX admite ~1,5 km, un RS-485 puede llegar a 1,2 km, alimentación auxiliar a sirenas se limita por caída de tensión". NO debería responder con datos de productos hasta tener al menos uno de los dos ejes acotado.

**Calidad de los chunks:**

- F1, F2, F3 son todos chunks del mismo manual MIE-MI-580 p.12 con headers diferentes ("Cableado", "Como norma general...", "Cableado de señalización y control") pero contenido prácticamente idéntico — patrón claro de duplicación + headers arbitrarios que son trozos de oraciones del texto, no secciones.
- F4 (MIE-MI-600 ZXSe) y F5 (MIE-MI-530 ZXe) son del mismo fabricante con secciones de "Cables recomendados" — útiles pero el bot omite que MIE-MI-600 sí menciona "Longitud máxima del lazo es de 1,5 km" según texto referenciado por el propio bot (pero el chunk no lo muestra explícitamente — verificar).
- Ningún chunk responde unívocamente a "distancia máxima"; los datos como 40Ω, 0,5μF, sección 1,5mm² son parámetros eléctricos del cable, no longitud.

**Comparación con bot:**

- El bot NO se limitó a pedir clarificación: respondió primero con un cuadro técnico para dos productos (Vision LT y Serie ZX), citando "1,5 km de lazo", "40 Ω", "0,5 μF", etc., y SOLO al final añadió la pregunta. Esto es esencialmente una respuesta dual: "te doy todo lo que tengo, y luego dime qué necesitas".
- En behavior label técnico debería catalogarse como `answer_with_caveat` o `answer_then_clarify`, no como `ask_clarification` puro. **El label "observed_behavior: ask_clarification" del YAML es incorrecto** — el bot SÍ respondió con afirmaciones técnicas concretas.
- Riesgo: el técnico podría tomar el "1,5 km" como respuesta y no leer la pregunta final, aplicándolo a un equipo distinto.

**Veredicto:**
- [x] **De acuerdo** con el judge en el dictamen final (FAIL por behavior_match), pero **EN DESACUERDO con la marca "🐛 BUG candidato"**.
- **Análisis del supuesto bug:** El flag dice "observed==expected pero el judge dice behavior_match=False". Esto NO es un bug del judge: el `observed_behavior` que registró el clasificador automático ES incorrecto (clasificó la respuesta como ask_clarification porque termina con una pregunta, ignorando que el cuerpo principal es una respuesta técnica). El judge LLM, leyendo la respuesta completa, detectó que conductualmente el bot respondió en lugar de clarificar y marcó behavior_match=False con razón. **El bug está en el clasificador de behavior, no en el judge.**
- **Dimensión equivocada(s) del judge:** ninguna — el judge acertó.
- **Nota / por qué:** El judge es el componente correcto del pipeline en este caso. Lo que falla es la heurística que asigna `observed_behavior` (probablemente busca patrones tipo "¿qué modelo...?" sin pesar el cuerpo de la respuesta). Recomendación: revisar la lógica de etiquetado de `observed_behavior` para que cuente la proporción de contenido afirmativo vs interrogativo, o pedir al propio LLM que clasifique el comportamiento.
- **Origen del problema:** clasificador de `observed_behavior` (heurística superficial) + comportamiento ambiguo del bot ("responde y de paso pregunta"). El bot debería abstenerse de responder con números hasta tener el modelo.

---

## mc007 — judge dice **PASS ✓** · (7/8)

**Pregunta del técnico:** El sistema me da fault

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 2/4 hits · missing: `['código', 'fabricante']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID2000` · *Estado: **FALLO** (fecha) (hora) (descripción) (tipo de equipo) o (identificación del fallo)* · `MFDT180` p.53 · sim 0.75

```
Estado: **FALLO**
(fecha)
(hora)
(descripción) (tipo de equipo) o (identificación del fallo)

Estado: **FALLO**
(fecha)
(hora)
(descripción) (tipo de equipo) o (identificación del fallo)

Panel ID2000 - Manual de funcionamiento
Apéndice 1
MF-DT-180
       NOTIFIER ESPAÑA
  A1 - 6
ESTADO PANEL: FALLO
Esta condición se produce por varias razones: algunas a
causa del funcionamiento incorrecto de un sensor o
módulo remotos, otras debido mal funcionamiento del
panel o sistema.
También se incluye en esta categoría el ‘FALLO
ALIMENTACIÓN, que señaliza un fallo de baterías, fuente
de alimentación principal o circuito del cargador, y el
‘FALLO DE SISTEMA’ que indica un fallo del
microprocesador.
La condición de FALLO persiste hasta que queda anulada
por otra prioritaria o hasta que se elimina pulsando la
tecla REARME.
El evento puede ‘aceptarse’ en el panel mediante la tecla
ACEPTAR, si es así, el panel permanecería en estado de
‘FALLO’.
El estado de los leds y equipos externos es el siguiente:
LEDS:
ALIMENTACIÓN (verde):
Si la alimentación es correcta:
ILUMINADO
FALLO DE TIERRA/
F.ALIMENTACIÓN/
FALLO DE SISTEMA (ámbar):
no aceptado:
INTERMIT.
aceptado:
FIJO
Leds de zonas (zonas en las que se ha detectado fallos
en sensores/módulos - ámbar):
no aceptados:
INTERMITENTE
aceptados:
INTERMITENTE
La pantalla muestra el siguiente mensaje:
Durante dos minutos aproximadamente tras haber
aceptado una el Fallo, la segunda línea de la pantalla
muestra un mensaje que avanza horizontalmente (utilice
las teclas 
 y 
 para examinar el texto) y que explica
detalladamente el FALLO: :
(tipo de fallo) (número de equipo) (zona) (tipo) (valor
analógico en el momento de la alarma (ubicación) (fecha
y hora de la alarma) e indicación de si existen más
fallos: ‘MÁS: PULSE 
 o 
’.
Estado: **FALLO**
(fech
[… contenido truncado para legibilidad]
```

**[F2]** `ID2000` · *3.3 Fallo* · `MFDT180` p.10 · sim 0.77

```
3.3
Fallo

3.3
Fallo

Panel ID2000 - Manual de funcionamiento
Alarmas automáticas - Qué hacer
MF-DT-180
       NOTIFIER ESPAÑA
       7
3.3
Fallo
Acciones automáticas del panel - Si el sistema
identifica una avería, el panel realiza lo siguiente de forma
automática:
a. Activa el zumbador de FALLO (de forma intermitente
si es un FALLO DE ALIMENTACIÓN).
b. Se iluminan uno o más leds ámbar de FALLO y los
leds de ZONA en FALLO correspondientes.
c. Activa cualquier salida de control asociada en la Matriz
de control con los eventos de fallo.
d. Visualiza en pantalla e imprime (si la impresora está
instalada y habilitada) información sobre el evento.
Nota: Si se trata de un fallo de sensor, en pantalla sólo
se indica el punto de origen o una breve referencia.
e. Activa el relé de transferencia de avería (para alertar
automáticamente al centro de mantenimiento).
Acciones recomendadas para el usuario:
1
Pulse la tecla ACEPTAR. En pantalla aparece
información sobre la avería. Los leds pasan a
iluminarse de forma fija. La sirena de fallo se activa de
forma intermitente (un pitido cada 2 minutos).
2
Si el fallo está relacionado con un sensor o módulo
específico, compruebe el equipo para poder determinar
la causa de la avería y solucionarla.
3
En cualquier otro caso, anote una descripción
completa de la avería y notifique a la empresa de
mantenimiento autorizada.
4
Una vez se haya eliminado la causa de la avería, pulse
la tecla REARME.
Nota:
Si en pantalla aparece el siguiente mensaje: “Fallo
sistema 40 - Watchdog de CPU principal
activado”, también es necesario pulsar la tecla
SILENCIAR SIRENAS para silenciar el zumbador
de fallo.
Note: Si los mensajes en pantalla no se pueden leer con
claridad, ajuste el contraste de la pantalla (véase la
Sección 4.7.3).
```

**[F3]** `ID2000` · *2 Si el fallo está relacionado con un sensor o módulo específico, compruebe el equipo para poder determinar la causa de * · `MFDT180` p.10 · sim 0.78

```
2
Si el fallo está relacionado con un sensor o módulo
específico, compruebe el equipo para poder determinar
la causa de la avería y solucionarla.

2
Si el fallo está relacionado con un sensor o módulo
específico, compruebe el equipo para poder determinar
la causa de la avería y solucionarla.

Panel ID2000 - Manual de funcionamiento
Alarmas automáticas - Qué hacer
MF-DT-180
       NOTIFIER ESPAÑA
       7
3.3
Fallo
Acciones automáticas del panel - Si el sistema
identifica una avería, el panel realiza lo siguiente de forma
automática:
a. Activa el zumbador de FALLO (de forma intermitente
si es un FALLO DE ALIMENTACIÓN).
b. Se iluminan uno o más leds ámbar de FALLO y los
leds de ZONA en FALLO correspondientes.
c. Activa cualquier salida de control asociada en la Matriz
de control con los eventos de fallo.
d. Visualiza en pantalla e imprime (si la impresora está
instalada y habilitada) información sobre el evento.
Nota: Si se trata de un fallo de sensor, en pantalla sólo
se indica el punto de origen o una breve referencia.
e. Activa el relé de transferencia de avería (para alertar
automáticamente al centro de mantenimiento).
Acciones recomendadas para el usuario:
1
Pulse la tecla ACEPTAR. En pantalla aparece
información sobre la avería. Los leds pasan a
iluminarse de forma fija. La sirena de fallo se activa de
forma intermitente (un pitido cada 2 minutos).
2
Si el fallo está relacionado con un sensor o módulo
específico, compruebe el equipo para poder determinar
la causa de la avería y solucionarla.
3
En cualquier otro caso, anote una descripción
completa de la avería y notifique a la empresa de
mantenimiento autorizada.
4
Una vez se haya eliminado la causa de la avería, pulse
la tecla REARME.
Nota:
Si en pantalla aparece el siguiente mensaje: “Fallo
sistema 40 - Watchdog d
[… contenido truncado para legibilidad]
```

**[F4]** `ID2000` · *Nota:Si se trata de un fallo de sensor, en pantalla sólo se indica el punto de origen o una breve referencia.* · `MFDT180` p.10 · sim 0.77

```
Nota:Si se trata de un fallo de sensor, en pantalla sólo
se indica el punto de origen o una breve referencia.

Nota:Si se trata de un fallo de sensor, en pantalla sólo
se indica el punto de origen o una breve referencia.

Panel ID2000 - Manual de funcionamiento
Alarmas automáticas - Qué hacer
MF-DT-180
       NOTIFIER ESPAÑA
       7
3.3
Fallo
Acciones automáticas del panel - Si el sistema
identifica una avería, el panel realiza lo siguiente de forma
automática:
a. Activa el zumbador de FALLO (de forma intermitente
si es un FALLO DE ALIMENTACIÓN).
b. Se iluminan uno o más leds ámbar de FALLO y los
leds de ZONA en FALLO correspondientes.
c. Activa cualquier salida de control asociada en la Matriz
de control con los eventos de fallo.
d. Visualiza en pantalla e imprime (si la impresora está
instalada y habilitada) información sobre el evento.
Nota: Si se trata de un fallo de sensor, en pantalla sólo
se indica el punto de origen o una breve referencia.
e. Activa el relé de transferencia de avería (para alertar
automáticamente al centro de mantenimiento).
Acciones recomendadas para el usuario:
1
Pulse la tecla ACEPTAR. En pantalla aparece
información sobre la avería. Los leds pasan a
iluminarse de forma fija. La sirena de fallo se activa de
forma intermitente (un pitido cada 2 minutos).
2
Si el fallo está relacionado con un sensor o módulo
específico, compruebe el equipo para poder determinar
la causa de la avería y solucionarla.
3
En cualquier otro caso, anote una descripción
completa de la avería y notifique a la empresa de
mantenimiento autorizada.
4
Una vez se haya eliminado la causa de la avería, pulse
la tecla REARME.
Nota:
Si en pantalla aparece el siguiente mensaje: “Fallo
sistema 40 - Watchdog de CPU principal
activado”, también es necesario pulsar la tecla
SILENCIA
[… contenido truncado para legibilidad]
```

**[F5]** `ID1000` · *34 Este fallo puede indicar lo siguiente:* · `MFDT212` p.39 · sim 0.75

```
34
Este fallo puede indicar lo siguiente:

34
Este fallo puede indicar lo siguiente:

Manual de Funcionamiento de la Serie ID1000
MF-DT-212
35
NOTIFIER ESPAÑA, S.A.
CÓDIGOS DE AVERÍAS - POSIBLES CAUSAS Y SOLUCIONES
1
La tarjeta de lazo no está instalada o falla su respuesta. Las  posibles causas pueden ser:
- Que se haya conectado un cable de cinta de forma incorrecta,
- que el cable de cinta esté desconectado, o un
- fallo de la tarjeta de lazo.
Como último recurso, cambie la tarjeta de lazo.
5
La tarjeta CPU del lazo realizó un rearme de alimentación. Posible causa:
- Fallo de tarjeta de lazo
Cambie la tarjeta de lazo.
9
Cortocircuito en el lazo X. Si hay aisladores instalados, el sistema muestra  SIN RESPUESTA/
AUSENTES para los equipos situados entre los puntos de aislamiento.
Desconecte la sección afectada del lazo y utilice un multímetro para encontrar el fallo.
13
Indica que se ha instalado un equipo sin ajustarlo a una dirección válida, es decir, que se ha
dejado con el valor por defecto de fábrica ‘00’.
17, 21
Ambos indican un fallo en la tarjeta de lazo.
Reemplace la tarjeta de lazo.
25
Los datos procedentes de un equipo de lazo están corruptos. Compruebe:
- La continuidad del lazo.
- Que la pantalla esté conectada a tierra en un sólo punto (normalmente al panel).
- Que los supresores de ferrita estén instalados en el cableado del lazo a la central.
32
Este fallo indica que el periférico no responde al código enviado o que no se ha conectado el
tercer equipo (esto, normalmente, indicaría un fallo en el equipo externo).
Primero sustituya la unidad periférica con un monitor RS232 o un equipo que funcione. Si funciona,
sustituya la unidad. Si no funciona, cambie la Placa CPU.
33
Indica un fallo en la fuente de alimentación de entrada. Compruebe lo siguiente:
- Si
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo de central estás usando y qué aparece exactamente en la pantalla (mensaje de texto, número de fallo, zona afectada)?

El mismo síntoma "fault" puede tener causas muy distintas según el equipo, y necesito esos datos para darte el diagnóstico correcto.
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

**Razón del judge:** La pregunta 'el sistema me da fault' es ambigua: no especifica modelo de central ni descripción del fallo en pantalla. El bot pide correctamente UN detalle concreto (modelo + mensaje en pantalla), lo cual es la conducta esperada 'ask_clarification'. No hace afirmaciones técnicas inventadas, y la solicitud de clarificación es pertinente dado que los fragmentos F1-F5 cubren múltiples productos (ID2000, ID1000) y múltiples tipos de fallo con causas distintas.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración solicitando información concreta: (1) modelo de central o equipo que muestra el fault; (2) mensaje exacto en pantalla (texto literal, números, código); (3) zona/dirección afectada; (4) leds que se han iluminado. Esta especificidad es clave porque "fault" en ID2000 vs "Fallo de Sistema 40" vs un código numérico (1, 5, 9, 13, 17, 21, 25, 32, 33, 34 según F5 de ID1000) implican procedimientos totalmente distintos.

**Calidad de los chunks:**

- F2, F3, F4 son todos del mismo manual MFDT180 p.10 con headers diferentes — patrón claro de duplicación. Headers ("2 Si el fallo...", "Nota: Si se trata...") son fragmentos numerados del propio texto, no secciones — patrón de header arbitrario.
- F1 corresponde al Apéndice (MFDT180 p.53) con texto sobre estado FALLO.
- F5 (ID1000) trae la tabla más útil para diagnóstico (códigos 1, 5, 9, 13, 17, 21, 25, 32, 33, 34 con causas y soluciones).
- Mismatch parcial section vs contenido: los chunks de la sección 3.3 "Fallo" repiten contenido de la página completa con headers que apuntan a distintos sub-puntos.

**Comparación con bot:**

- Sí pidió clarificación correctamente, listando explícitamente los datos que necesita: modelo, mensaje en pantalla, número de fallo, zona afectada. Especificidad excelente.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Clarificación de calidad alta — pide datos accionables y no genéricos.
- **Origen del problema:** N/A.

---

## mc008 — judge dice **PASS ✓** · (8/8)

**Pregunta del técnico:** ¿Cómo pongo la instalación en servicio?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 2/3 hits · missing: `['fabricante']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID50` · *Puesta en marcha* · `MIDT155` p.28 · sim 0.78

```
Puesta en marcha

Puesta en marcha

Puesta en marcha
Panel ID50 - Manual de instalación, puesta en marcha y configuración
MI-DT-155
NOTIFIER ESPAÑA
     23
4
Puesta en marcha
4.1
Introducción
Esta sección describe cómo poner en marcha el panel
de control ID50 y prepararlo para su configuración. Para
poner en marcha el panel ID50 siga los pasos que se
indican a continuación. La información relacionada con
la configuración del panel se detalla en la sección 5:
Configuración.
1 Compruebe que el panel se ha montado e instalado
correctamente, consulte la sección 4.2:
Comprobaciones preliminares.
2 Compruebe la configuración interna del panel, sección
4.3 Comprobaciones internas
3 Compruebe y conecte el cableado externo, consulte
la sección 4.4, Comprobaciones del cableado
externo.
4 Configure el panel para que se adapte a los requisitos
de su sistema, consulte la sección 5:
Configuración.
5 Compruebe que el sistema funciona correctamente.
4.2
Comprobaciones preliminares
Antes de conectar la alimentación principal al panel,
compruebe que:
a. Todas las tarjetas están instaladas correctamente.
b. El cableado interno está correctamente conectado.
c. El cableado de lazo y los circuitos de sirena externos
NO  están todavía conectados a la placa base (PCB).
d. Las resistencias de final de línea 6k8 están conectadas
a las salidas de sirena.
e. Las resistencias finales 150R están conectadas al
primer y último panel de la conexión de
comunicaciones RS485.
Los cinco pasos siguientes están relacionados con la
puesta en marcha del cableado externo:
a. Compruebe la continuidad del cableado del lazo, los
equipos invertidos, cortocircuitos y circuitos abiertos.
b. Conecte el cableado del lazo al panel.
c. Compruebe que no haya averías después de la
conexión del lazo al panel.
Nota:
La longi
[… contenido truncado para legibilidad]
```

**[F2]** `ID50` · *4.7 Pruebas en la puesta en marcha* · `MIDT155` p.39 · sim 0.78

```
4.7
Pruebas en la puesta en marcha

4.7
Pruebas en la puesta en marcha

Panel ID50 - Manual de instalación, puesta en marcha y configuración
Puesta en marcha
MI-DT-155
NOTIFIER ESPAÑA
     34
4.6
Configuración y entrega
Tras haber conectado todo el cableado externo al panel y
una vez la pantalla muestre el mensaje “Sistema estado
normal”, ya puede configurar el panel según los requisitos
de su sistema. Si desea más información sobre la
configuración del sistema, consulte la sección 5:
Configuración.
Tras haber completado la configuración y rectificado todas
las averías surgidas, el sistema estará preparado para llevar
a cabo las pruebas de puesta en marcha (véase la sección
4.7: Pruebas en la puesta en marcha), tal y como
requieren las normas, antes de entregar el panel al usuario.
4.7
Pruebas en la puesta en marcha
Una vez se haya comprobado todo el cableado, el panel
ID50 y el sistema estarán preparados para la puesta en
marcha y la configuración del software. Puede cancelar el
proceso de configuración del software en cualquier momento.
Los párrafos siguientes son una guía práctica para llevar a
cabo la puesta en marcha del sistema. Si finaliza con éxito
los pasos indicados a continuación, el panel funcionará
correctamente.
Siga lo indicado a continuación para entrar en el Modo de
puesta en marcha
1 Mientras la pantalla muestra el mensaje ‘Sistema estado
normal’, pulse la tecla ‘
’. La pantalla le pedirá un código
de acceso, tal y como se indica a continuación:
Nota:Si la llave está colocada y habilitada, el menú de nivel
2 aparecerá en pantalla de forma automática.
2 Utilizando el teclado de la central, (véase el manual de
funcionamiento del panel ID50, sección 4.6: Teclas
alfanuméricas. Ref.: 997-264), introduzca el
a. Código de acceso del nivel 2, o
b. Código de ac
[… contenido truncado para legibilidad]
```

**[F3]** `ID1000` · *5.1   Comprobaciones Preliminares* · `MIDT212` p.24 · sim 0.78

```
5.1   Comprobaciones Preliminares

5.1   Comprobaciones Preliminares

Manual de Instalación y Puesta en Marcha de la Serie ID1000
MI-DT-212
20
NOTIFIER ESPAÑA, S.A.
5.
5.5.
5.
5.
PUESTA EN MARCHA
PUESTA EN MARCHA
PUESTA EN MARCHA
PUESTA EN MARCHA
PUESTA EN MARCHA
Los detalles que se especifican a continuación muestran cómo conectar el panel de control para que
esté preparada para la programación (configuración). Si desea más detalles sobre la programación
de los paneles de control de la Serie ID1000, consulte el Manual de Programación de la Serie ID1000,
997-340-003
Los paneles de control de la serie ID1000 proporcionan unas rutinas de diagnóstico y supervisión
generales muy útiles durante la puesta en marcha del sistema. Los mensajes de diagnóstico que
aparecen visualizados en la pantalla LCD están especificados en el Apéndice 1.
Recuerde que las condiciones de AVERÍA están enclavadas en los paneles de control de la serie
ID1000 y no desaparecen de manera automática cuando la avería relacionada deja de existir. Al pulsar
primero la tecla "SILENCIO INTERNO" se silenciará el zumbador interno y pulsando "REARME", se
borrará la pantalla de avería si dicha avería ha desaparacecido. Sin embargo, si la pantalla LCD
muestra en pantalla "Fallo de Sistema 40 - Fallo de CPU” necesitará pulsar "SILENCIO SIRENAS"
antes de silenciar el zumbador interno y rearmar la condición.
5.1   Comprobaciones Preliminares
Compruebe que todas las placas del circuito están correctamente instaladas y los conectores de la
instalación eléctrica interna están correctamente instalados. El cableado del lazo y los circuitos de
sirena externos no deben conectarse todavía.
Asegúrese que las resistencias de final de línea de 47K están conectadas a las salidas de sirena y
que el terminal +vo de la "Alimentac
[… contenido truncado para legibilidad]
```

**[F4]** `ID2000` · *4 Los circuitos de salida 3 y 4 están configurados como relés si así se requiere.* · `MIDT180` p.43 · sim 0.78

```
4
Los circuitos de salida 3 y 4 están configurados como
relés si así se requiere.

4
Los circuitos de salida 3 y 4 están configurados como
relés si así se requiere.

Panel ID2000 - Manual de instalación y puesta en marcha
Puesta en marcha
MI-DT-180
       NOTIFIER ESPAÑA
       39
8
Puesta en marcha
8.1
Introducción
Para poner la central en un estado funcional que permita
realizar la configuración, siga el procedimiento descrito a
continuación. En el Manual de configuración del panel
ID3000 encontrará información sobre cómo configurar
dicho panel.
Los paneles de la serie ID2000 proporcionan rutinas de
diagnóstico y supervisión de averías que demostrarán ser
muy útiles durante la puesta en marcha del sistema. Los
mensajes de diagnóstico que aparecen en la pantalla LCD
se indican en el Apéndice 1.
Debe recordar los siguientes puntos sobre las condiciones
de AVERÍA cuando realice la puesta en marcha de los
paneles ID2000.
Las averías se pueden originar a partir de:
a. Un desequilibrio en la configuración entre el diseño de
la instalación y la configuración del panel, o
condiciones externas, como la proximidad de una
fuente de radiofrecuencias, con un efecto adverso en
el panel, o
c. El fallo de un módulo, como por ejemplo la fuente de
alimentación o la placa de microprocesador.
El Apéndice 1 describe cómo identificar las averías que
pertenecen a las categorías indicadas.
8.2
Comprobaciones preliminares
Antes de conectar la alimentación, compruebe que:
1
Todas las placas de circuito están correctamente
instaladas.
2
Todo el cableado interno está conectado
correctamente.
3
El cableado del lazo y los circuitos de salida externos
NO están todavía conectados.
4
Los circuitos de salida 3 y 4 están configurados como
relés si así se requiere.
5
Los circuitos de salida de sirena di
[… contenido truncado para legibilidad]
```

**[F5]** `ID50` · *Puesta en marcha* · `MIDT155` p.39 · sim 0.78

```
Puesta en marcha

Puesta en marcha

Panel ID50 - Manual de instalación, puesta en marcha y configuración
Puesta en marcha
MI-DT-155
NOTIFIER ESPAÑA
     34
4.6
Configuración y entrega
Tras haber conectado todo el cableado externo al panel y
una vez la pantalla muestre el mensaje “Sistema estado
normal”, ya puede configurar el panel según los requisitos
de su sistema. Si desea más información sobre la
configuración del sistema, consulte la sección 5:
Configuración.
Tras haber completado la configuración y rectificado todas
las averías surgidas, el sistema estará preparado para llevar
a cabo las pruebas de puesta en marcha (véase la sección
4.7: Pruebas en la puesta en marcha), tal y como
requieren las normas, antes de entregar el panel al usuario.
4.7
Pruebas en la puesta en marcha
Una vez se haya comprobado todo el cableado, el panel
ID50 y el sistema estarán preparados para la puesta en
marcha y la configuración del software. Puede cancelar el
proceso de configuración del software en cualquier momento.
Los párrafos siguientes son una guía práctica para llevar a
cabo la puesta en marcha del sistema. Si finaliza con éxito
los pasos indicados a continuación, el panel funcionará
correctamente.
Siga lo indicado a continuación para entrar en el Modo de
puesta en marcha
1 Mientras la pantalla muestra el mensaje ‘Sistema estado
normal’, pulse la tecla ‘
’. La pantalla le pedirá un código
de acceso, tal y como se indica a continuación:
Nota:Si la llave está colocada y habilitada, el menú de nivel
2 aparecerá en pantalla de forma automática.
2 Utilizando el teclado de la central, (véase el manual de
funcionamiento del panel ID50, sección 4.6: Teclas
alfanuméricas. Ref.: 997-264), introduzca el
a. Código de acceso del nivel 2, o
b. Código de acceso de nivel 3.
Consulte el apéndic
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo de central estás poniendo en servicio?

Los fragmentos que tengo cubren procedimientos de puesta en marcha para distintos paneles, y los pasos concretos (comprobaciones previas, resistencias de final de línea, secuencia de conexión) varían entre modelos. Dime el modelo exacto y te doy el procedimiento paso a paso.
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

**Razón del judge:** La pregunta '¿Cómo pongo la instalación en servicio?' es ambigua porque los fragmentos F1-F4 cubren procedimientos de puesta en marcha para distintos modelos (ID50, ID1000, ID2000) con pasos y especificaciones técnicas diferentes (resistencias de final de línea 6k8 vs 47K vs 4k7, etc.). El bot pide correctamente un único detalle concreto —el modelo de central— antes de responder, lo cual es exactamente la conducta esperada (ask_clarification). No hace afirmaciones técnicas inventadas y su justif

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia:**

El bot debería pedir aclaración pidiendo: (1) modelo concreto de la central a poner en servicio (las resistencias de final de línea, secuencia de comprobaciones internas, códigos de acceso y procedimientos varían: ID50 usa 6k8 en sirenas y 150R en RS485; ID1000 usa 47K en sirenas; ID2000 tiene 4 circuitos de salida configurables). Opcionalmente puede señalar que el procedimiento genérico EN54 se compone de: comprobaciones preliminares (cableado interno, FDL conectadas) → comprobación externa de continuidad → conexión del lazo → verificación de averías → configuración → pruebas de puesta en marcha.

**Calidad de los chunks:**

- F1 y F5 son del mismo manual MIDT155 (ID50) — duplicación parcial.
- F2 también de MIDT155 p.39 — tres chunks del mismo manual entre cinco.
- Headers de F1 ("Puesta en marcha") y F5 ("Puesta en marcha") son idénticos pero apuntan a páginas distintas (p.28 y p.39) — patrón de header genérico y poco discriminante.
- F4 (ID2000) tiene como header un punto numerado suelto ("4 Los circuitos de salida 3 y 4..."), no una sección — patrón de header arbitrario.

**Comparación con bot:**

- Sí pidió clarificación correctamente, mencionando que los pasos varían entre modelos y ofreciendo continuar con el procedimiento paso a paso una vez tenga el modelo.
- No respondió asumiendo contexto.

**Veredicto:**
- [x] **De acuerdo** con el judge (PASS)
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Clarificación correcta. Podría haber sido aún más útil listando los modelos del corpus (ID50, ID1000, ID2000) explícitamente como hizo en mc003.
- **Origen del problema:** N/A.

---

