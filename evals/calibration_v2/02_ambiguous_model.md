# Calibración del judge v2 — categoría `ambiguous_model` (8 preguntas)

**Origen:** `logs/eval_20260502T152857Z.json` (eval del 2 mayo 2026).

**Categoría:** Nombre de modelo genérico o familia -> bot debe pedir aclaración antes de responder.

## Cómo evaluar cada caso

Para cada pregunta lees: **query → fragmentos que el bot vio → respuesta del bot → veredicto del judge**.

1. Verifica mentalmente si cada afirmación del bot está respaldada por al menos un fragmento. Si dice "40 Ω" y un fragmento lo menciona, ok. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.
2. Verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML.
3. Marca **De acuerdo** o **En desacuerdo** y, si estás en desacuerdo, indica qué dimensión del judge falló (faithful / relevant / helpful / honest / behavior_match) y por qué.

**No necesitas saber PCI**: es lectura comparativa entre lo que dicen los fragmentos y lo que dice el bot.

Los flags **⚠️** y **🐛** que verás arriba de algunos casos marcan patrones sospechosos que Claude detectó automáticamente — úsalos como pista pero no como conclusión.

---

## am001 — judge dice **PASS ✓** · (1/8)

**Pregunta del técnico:** ¿Cómo programo el sistema 5000?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 0/4 hits · missing: `['system 5000', 'systema 5000', 'notifier', 'cuál']` · **keyword_pass:** `False`

> _Notas YAML: En BD hay 'System 5000' y 'Systema 5000' (ambos Notifier). Bot debe listar candidatos._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `Sistema 5000` · *B F* · `MNDT060` p.38 · sim 0.65

```
B
F (continuación)

[TABLA EXTRAÍDA]
| EEEEE |  | FFFFF | GGGGG |  | HHHHH |  |  |  |  |  |  |  | 
----------------------------------------
 | b+ a+ a- b- b | + a+ | a- b- | b+ a+ a- | b- b+ a+ a- | b- |  |  | Expansor d | e Circuito In | dicador | ICE-4 |  | 
 |  |  |  |  |  |  |  |  | Opcional. La | s Posiciones E | , F, G y | H sólo |  | 
 |  |  |  |  |  |  |  |  | son activas s | i está instalad | o este ta | blero. |  | 
 | AAAAA |  | BBBBB | CCCCC |  | DDDDD |  |  |  | Circuito |  |  |  | 
 |  |  |  |  |  |  |  |  | de | Dispositivo |  |  |  | 
 | b+ a+ a- b- b+ | a+ | a- b- | b+ a+ a- | b- b+ a+ a- | b- |  |  | Indi | cador Típic | o |  |  | 
 |  |  |  |  |  |  |  |  | Est | ilo Y NFPA |  |  |  | 
 |  |  |  |  |  |  |  |  |  |  |  | de Disp | ositivo | I
 |  |  |  |  |  |  |  |  | EEEEELLLLLRRRRR | 44444.....77777KKKKK,,,,, 11111/////22222 wwwwwaaaaatttttttttt,,,,, |  |  |  | 
 |  |  |  |  |  |  |  |  | nnnnn***** | PPPPPiiiiieeeeezzzzzaaaaa 7777711111222225555522222..... 55555 |  | Circ | uito | 
 |  |  |  |  |  |  |  |  |  |  |  | ndic | ador | 
 |  |  |  |  |  |  |  |  |  |  |  | Típico | Estilo | Z
 |  |  |  |  |  |  |  |  |  |  |  | NF | PA | 
 |  |  |  |  |  |  |  |  |  | UUUUU | .....LLLLL..... llllliiiiisssssttttteeeeeddddd |  |  | 
 |  |  |  |  |  |  |  |  |  |  | 2222244444 VVVVVDDDDDCCCCC |  |  | 
 |  |  |  |  |  |  |  |  |  | PPPPPooooolllll | aaaaarrrrriiiiizzzzzeeeeeddddd BBBBBeeeeelllll | lllllsssss |  | 
 |  | A |  |  |  |  | E |  |  |  |  |  |  | 
 |  |  |  |  |  |  |  |  |  | UUUUU | .....LLLLL..... llllliiiiisssssttttteeeeeddddd |  |  | 
 |  |  |  |  |  |  |  |  |  |  | 2222244444 VVVVVDDDDDCCCCC |  |  | 
 |  |  |  |  |  |  |  |  |  | PPPPPooooolllllaaaaa | rrrrriiiiizzzzzeeeeeddddd HHHHHooooorrrrr | nnnnnsssss |  | 
 |  | B |  |  |  |  | F |
[… contenido truncado para legibilidad]
```

**[F2]** `Sistema 5000` · *Paso 5 Instale los cuatro tornillos retirados anteriormente, introduciéndolos en los separadores a través de la parte po* · `MNDT060` p.28 · sim 0.65

```
Paso 5
Instale los cuatro tornillos
retirados
anteriormente,
introduciéndolos
en
los
separadores a través de la parte
posterior del Tablero Expansor.

Paso 5
Instale los cuatro tornillos
retirados
anteriormente,
introduciéndolos
en
los
separadores a través de la parte
posterior del Tablero Expansor.

MN-DT-060
28
NOTIFIER ESPAÑA, S.A.
Paso 3
Repita los Pasos 1 y 2 para los tres tornillos restantes del módulo.
Figura 3-6: Montaje de Expansores de Módulos Opcionales
Paso 1
Retire UN tornillo de
soporte de módulo y
consérvelo para su
utilización posterior.
Paso 2
Sustituya el tornillo por un
separador de módulo.
Módulo
Módulo
Módulo
Módulo
Módulo
Módulo
Módulo
Módulo
Módulo
Módulo
Paso 5
Instale los cuatro tornillos
retirados 
anteriormente,
introduciéndolos 
en 
los
separadores a través de la parte
posterior del Tablero Expansor.
Módulo  Tablero
Módulo  Tablero
Módulo  Tablero
Módulo  Tablero
Módulo  Tablero
                   Expansor
                   Expansor
                   Expansor
                   Expansor
                   Expansor
Módulo            Tablero
Módulo            Tablero
Módulo            Tablero
Módulo            Tablero
Módulo            Tablero
                          Expansor
                          Expansor
                          Expansor
                          Expansor
                          Expansor
Paso 4
Inserte los pivotes en
el Tablero Expansor,
introduciéndolos en el
conector del módulo, y
ejerza presión sobre los
dos tableros  a la vez
para asegurarse de que
los pivotes estén
c o r r e c t a m e n t e
alineados.
```

**[F3]** `Sistema 5000` · *REQUISITOS RFI DEL CANADÁ* · `MNDT060` p.2 · sim 0.65

```
REQUISITOS RFI DEL CANADÁ

REQUISITOS RFI DEL CANADÁ

MN-DT-060
2
NOTIFIER ESPAÑA, S.A.
AVISO DE FCC
AVISO: Este equipo genera, utiliza y puede irradiar energía de
radiofrecuencia y, si no se instala y utiliza tal como se especifica en
el manual de instrucciones, puede originar interferencia con las
radiocomunicaciones. Este equipo se ajusta a los límites de los
dispositivos de cálculo de clase A de conformidad con la Subparte
B de la parte 15 de las normas FCC, que están diseñados para proporcionar protección
razonable contra dichas interferencias, en cuyo caso los gastos de la eliminación de las
mismas correrán a cuenta del usuario.
REQUISITOS RFI DEL CANADÁ
Este aparato digital no sobrepasa los límites de la Clase A para las emisiones de
perturbaciones radioeléctricas de aparatos digitales, establecidas en las Normas de
Radiointerferencias del Ministerio Canadiense de Comunicaciones.
MN-DT-060
3
NOTIFIER ESPAÑA, S.A.
Sección Uno:
Sección Dos:
Sección Tres:
Sección Cuatro:
Sección Cinco:
Información General
Inventario del Sistema 5000
Paquete de Equipo Básico (BE-5000)
                Fuentes de Alimentación Opcionales del
Sistema 5000
Módulos de Iniciación Opcionales
Módulos Opcionales
Hardware de Caja Opcional
Equipo Opcional de Evacuación por voz
Módulos de Avisador Opcionales
Cajas del Sistema 5000
Instalación del Sistema 5000
Líneas Generales de la Instalación
Instalación del Bastidor
Montaje de las Fuentes de Alimentación
Montaje de ARM-4
Conexión de los Cables Planos de Fila
Montaje de los Expansores de Módulo
Montaje de los Módulos
Montaje de la CPU-5000
Cableado Local de los Módulos
Cableado de Arm-4
Cableado de la CPU-5000
Cableado de IZM-8
Cableado de ICM-4
Cableado de CRM-4
Fuentes de Alimentación
Fuente de Alimentación Principal MPS-24
Fuente de Alimentac
[… contenido truncado para legibilidad]
```

**[F4]** `Sistema 5000` · *BE-5000AA:  El Equipo Básico-5000AA incluye la CPU-5000, la MPS- 24BPCA, el Transformador 4000TA y un cable de cinta de * · `MNDT060` p.75 · sim 0.65

```
BE-5000AA:  El Equipo Básico-5000AA incluye la CPU-5000, la MPS-
24BPCA, el Transformador 4000TA y un cable de cinta de CPU de dos
posiciones.

BE-5000AA:  El Equipo Básico-5000AA incluye la CPU-5000, la MPS-
24BPCA, el Transformador 4000TA y un cable de cinta de CPU de dos
posiciones.

MN-DT-060
75
NOTIFIER ESPAÑA, S.A.
CAB-AA está constituido por una caja con una puerta que permiten el montaje semi-empotrado de un Sistema 5000
de pequeño tamaño (hasta tres módulos) entre pernos de 16 pulgadas situadas en el centro (?). CAB-AA también
puede montarse en una superficie. Además de la CPU-5000, incluyendo AIM-200. Los módulos se montan en los
raíles de la cabina, no siendo necesarios ensamblajes de bastidor opcionales. Una ubicación de montaje empotrada
permite la instalación de una Fuente de Alimentación Audio Visual AVPS-24 o un Tablero de Interfaz de Red NIB-
96 debajo de los módulos. La alimentación del Sistema 5000 en la CAB-AA requiere una Fuente de Alimentación
Principal MPS-24BPCA, que proporciona hasta 2,3 amps de alimentación de dispositivo indicador, y un
Transformador 4000TA.
BE-5000AA:  El Equipo Básico-5000AA incluye la CPU-5000, la MPS-
24BPCA, el Transformador 4000TA y un cable de cinta de CPU de dos
posiciones.
CAB-AA:Caja (14.5" ancho, 17" alto, 5" profundo) y puerta (14.57" ancho,17.25"
alto, 1.5 " profundo).
DP-AA:  El Panel de Revestimiento Interno cubre el área de la caja que rodea
a los módulos. Nota: El Panel de Revestimiento Interno es obligatorio para las
instalaciones del Sistema 5000/CAB-AA en Canadá.
Limitaciones del Sistema:
Capacidad limitada de voltaje de alimentación (cálculos básicos en MPS-24B).
La caja sólo puede contener baterías del rango de 6,5 a 12 amp-hora.
Ademas de la CPU-5000, sólo puede haber un máximo de dos módulos.
Soportará
[… contenido truncado para legibilidad]
```

**[F5]** `Sistema 5000` · *Table 1-2: Cabinet Configuration Options* · `MNDT060` p.8 · sim 0.65

```
Table 1-2: Cabinet Configuration Options

MN-DT-060
8
NOTIFIER ESPAÑA, S.A.
Tabla 1-1: Opciones de Configuración Física
Los módulos pueden compartir posiciones con tableros expansores y Fuentes de Alimentación Audio-
visuales como se ilustra en esta tabla.
1)   ARM-4 (notas 1 & 2)
1)   IZE-A y/o ARM-4 (notas 1 & 2)
2)   AVPS-24 (nota 2)
1)   ICE-4 y/o ARM-4 (notas 1 & 2)
2)   CRE-4 y/o ARM-4 (notas 1 & 2)
3)   AVPS-24 (nota 2)
1)   CRE-4 y/o ARM-4 (notas 1 & 2)
2)   AVPS-24 (nota 2)
1)   AVPS-24 (nota 2)
Permissible Position Sharing Combinations
Posiciones de Módulos
Primaios
4
4 u 8
4, 8, ó 12
4, 8, 12, ó 16
Cabina
CAB-A2
CAB-B2
CAB-C2
CAB-D2
Table 1-2: Cabinet Configuration Options
CPU-5000
IZM-8
ICM-4, TCM-2, TCM-4, VCM-4
CRM-4
DCM-4
Notas:
1) ARM-4 debe montarse debajo del CRM-4 o CRE-4 asociado, o en una posición adyacente
al mismo.
2) Se recomienda sólo cuando hay un límite de espacio.
Numero Máximo de Bastidores
1
1 ó 2
1, 2 ó 3
1, 2, 3, ó 4
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué aspecto concreto de la programación del Sistema 5000 necesitas, y qué modelo o componente específico estás usando (CPU-5000, módulos de iniciación, módulos de avisador, etc.)?

Los fragmentos disponibles cubren instalación física y cableado, pero la programación puede referirse a configuración de zonas, lógicas, módulos u otros aspectos. Con más detalle puedo orientarte mejor.
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

**Razón del judge:** La pregunta '¿Cómo programo el sistema 5000?' es ambigua: puede referirse a configuración de zonas, módulos, lógicas, etc. El bot correctamente pide un detalle concreto antes de responder, lo cual coincide con la conducta esperada 'ask_clarification'. Además, el fragmento V6 confirma que la programación del Sistema 5000 remite al Field Programming Manual (Documento 15584), información que el bot no vio en los fragmentos F, por lo que su cautela es justificada. El bot no hace afirmaciones técnica

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general del corpus Notifier`):**

Ante "sistema 5000" ambiguo, el bot debería pedir clarificación listando candidatos plausibles: "¿Te refieres al **System 5000** (Notifier, panel modular MN-DT-060) o al **Systema 5000** de otra serie?" y, una vez identificado, qué aspecto de programación (zonas, lógicas, módulos de entrada/salida, mensajes, contraseñas). El bot pide clarificación pero no enumera las dos variantes de la BD.

**Calidad de los chunks:**

- F1 contiene una `[TABLA EXTRAÍDA]` masivamente corrupta (caracteres "EEEEE/FFFFF/AAAAA" duplicados con ruido de OCR) — patrón sistémico de tabla mal extraída.
- F2 muestra duplicación masiva ("Paso 5" repetido literalmente).
- F3 tiene header "REQUISITOS RFI DEL CANADÁ" que no corresponde al contenido posterior (índice del manual) — mismatch header/contenido.
- Headers de chunks son fragmentos arbitrarios ("Sistema 5000" como section_header genérico para todos los F).

**Comparación con bot:**

- Pidió clarificación correctamente (behavior_match OK).
- Omisión: no listó las dos variantes "System 5000" vs "Systema 5000" según pide la nota YAML. Su clarificación es genérica ("qué aspecto / qué módulo").
- No inventó datos técnicos.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** El bot cumplió la conducta esperada (`ask_clarification`) y no afirmó nada falso. El keyword_pass=False es por keywords frágiles (la BD distingue 'System' vs 'Systema' pero el bot habla en castellano de "Sistema 5000"). Mejorable: que liste candidatos, pero no es FAIL.
- **Origen del problema:** chunk-extraction (tablas OCR corruptas) + behavior parcialmente mejorable (no enumera candidatos).

---

## am002 — judge dice **PASS ✓** · (2/8)

**Pregunta del técnico:** Mi central da error genérico al arrancar, ¿qué hago?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 2/4 hits · missing: `['error', 'mensaje']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID3000` · *Descripción: Descripción del panel Descripción de zona Avería          Lun 01-May-2000 11:20:07* · `MFDT190` p.29 · sim 0.85

```
Descripción: Descripción del panel
Descripción de zona
Avería          Lun 01-May-2000 11:20:07 (continuación)

 Descripción de avería
 Avería          Lun 01-May-2000 11:20:07
EVENTOS:
  Avería:
            01-May 10:45:31
Averías: ZONAS: 14;   
 1
 Descripción: Descripción del panel

 Mensaje de avería
 Avería          Lun 01-May-2000 11:20:07
EVENTOS:
  Avería:            01-May 10:15:06
Averías: 
 14; EVENTOS: 1
 Descripción: Descripción del panel
 Descripción de zona

 Avería          Lun 01-May-2000 11:20:07
ZONAS:
  Avería: ZONA   6
Averías: 
 3 EVENTOS: 1
 Descripción: Descripción del panel
 Descripción de zona
Avería          Lun 01-May-2000 

11:20:07
ZONAS:
 Avería: Zona    1
```

**[F2]** `ID3000` · *5.1.4 Menús* · `MFDT190` p.23 · sim 0.85

```
5.1.4
Menús

La pantalla - tabuladores, eventos y menús
Panel ID3000 - Manual de funcionamiento
MF-DT-190_B
       18
5
La pantalla - tabuladores,
eventos y menús
5.1
Introducción
5.1.1
Estado: NORMAL
La pantalla de “Estado: Normal” aparece
cuando:
a. No existe ninguna condición de alarma o
prueba, y
b. No se accede a ningún menú.
Otras indicaciones de estado NORMAL:
Led de ALIMENTACIÓN (verde)
ILUMINADO
Otros leds
APAGADOS
Zumbadores internos
APAGADOS
Circuitos de sirena internos
APAGADOS
Relés de ALARMA, AVERÍA
APAGADOS
Módulos de control
APAGADOS (a menos que se
activen por una acción auxiliar)
Los leds indicadores incorporados en los sensores y módulos
deben iluminarse de forma intermitente o estar apagados.
5.1.2
Tabuladores
Cuando se produce algún tipo de condición
que no es “Estado: Normal”, la pantalla muestra
los datos de los eventos en cuestión. Puede
que haya información sobre más de un tipo
de evento (por ejemplo, alarmas, averías,
menús, etc.). Cuando esto ocurre, la
información disponible se indica en varios
tabuladores (pestañas) en la parte inferior de
la pantalla.
5.1.3
Eventos
En las pantallas de eventos se muestran las
alarmas, prealarmas, averías, equipos
anulados, modo evacuación y activaciones de
entradas auxiliares. En el ejemplo, se muestra
una pantalla de avería. En los paneles
conectados en red, el texto de “descripción”
se sustituye por el tipo de panel, es decir,
maestro, esclavo 1, etc.
5.1.4
Menús
Los menús se organizan de forma jerárquica.
El primer menú es el de Usuario, a partir del
cual se puede acceder al resto de menús.
Estado:NORMAL   Lun 01-May-2000 11:20:07
PANTALLA
ACTUAL
OTRAS 
PANTALLAS
DISPONIBLES
 Alarma ZONA    2           04:52 Total
                                    1
 Descripción: Descripción del panel    Ln Mnn
 Texto d
[… contenido truncado para legibilidad]
```

**[F3]** `CCD-100` · *6. Una vez solucionado el problema, hay que rearmar la central.* · `55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT` p.27 · sim 0.85

```
6. Una vez solucionado el problema, hay que rearmar la central. (continuación)

[TABLA EXTRAÍDA]
Acciones | en fuera de | serv | icio | : |  |  |  |  |  |  | 
----------------------------------------
Las únicas | acciones qu | e se | pue | den tom | ar | en este | caso: |  |  |  | 
• Pulsar la | tecla de sile | nciar | zum | bador p | ar | a detene | r la indicac | ión | acústi | ca. | 
• Recuper | ar la alimenta | ción | de | RED (22 | 0 | V). |  |  |  |  | 
• Cambio d | e las batería | s por | otr | as carga | d | as. |  |  |  |  | 
6.4.7- M | odo fallo | de si | ste | ma |  |  |  |  |  |  | 
El estado | de fallo de si | stem | a s | e produce |  | cuando h | a ocurrido | al | guna si | tuac | ión crítica
en el siste | ma y este no | pued | e o | perar cor | re | ctament | e. La indica | ció | n de fa | llo d | e sistema
es la sigui | ente: |  |  |  |  |  |  |  |  |  | 
• Indicador | de fallo gen | eral a | ctiv | ado de f | or | ma fija. |  |  |  |  | 
• Indicador | de fuera de | servi | cio | activado | d | e forma fi | ja. |  |  |  | 
• Indicador | acústico act | ivado | de | forma fij | a | . |  |  |  |  | 
• Salida de | avería activ | ada. |  |  |  |  |  |  |  |  | 
6 | .5- ¿Qué | ha | ce | r en c | a | so de | alarma | o | aver | ía? | 
Las centra | les convenci | onale | s e | stán dise | ñ | adas pa | ra garantiz | ar | una efi | caz | respuesta
en caso de | alarma. Es | precis | o c | onocer el | e | quipo pa | ra actuar d | e f | orma c | orre | cta en una
situación c | rítica. IMPO | RTAN | TE | : Es nece | s | ario leer l | os pasos si | gu | ientes, | ya q | ue le será
de gran ay | uda en caso | de al | arm | a: |  |  |  |  |  |  | 
1. Lo princ | ipal en caso | de a | larm | a es MA | N | TENER | LA CALM | A, | la cent | ral d | ispara las
campan | as y s
[… contenido truncado para legibilidad]
```

**[F4]** `ID50/60` · *5.5.1.7 Retardo Fallo Red AC* · `MIDT156` p.49 · sim 0.85

```
5.5.1.7 Retardo Fallo Red AC

5.5.1.7 Retardo Fallo Red AC

Configuración
Centrales ID50/60 - Manual de instalación, puesta en marcha y configuración
MI-DT-156_C
     43
3
Pulse la tecla ‘
6 ’ para cambiar entre las dos opciones:
‘En cada alarma zona’ y ‘En cada alarma punto’.
4
Pulse ‘
4 ’ para regresar al menú de configuración. Los
cambios se guardarán al salir.
5.5.1.7 Retardo Fallo Red AC
Por defecto, un fallo de red se indica en 10 segundos. Esta
opción, permite que el retardo se amplíe a 60 minutos en
incrementos de un minuto. Un retardo en la indicación de
fallo de más de 30 segundos no cumple con EN54 (véase
más información a la izquierda). Para configurar un retardo
de salida de fallo, proceda como se indica a continuación:
1
Desde el menú de configuración, pulse la tecla ‘
1 ’
para entrar en el menú ‘Opciones de Central’. Primero
aparecerá la pantalla de Idioma.
2
Pulse las teclas ‘
2 /
8 ’ para visualizar las diferentes
opciones hasta que aparezca la pantalla de Retardo Fallo
Red AC.
3
Pulse la tecla ‘
6 ’ para cambiar el tiempo de retardo:
4
Utilice el teclado numérico para introducir el valor nuevo:
5
Pulse‘
4 ’ para regresar al menú de configuración. Todos
los cambios se salvarán al salir del menú.
5.5.1.8 Modo diagnósticos
Esta opción permite indicar de forma inmediata, sin retardo
de verificación, las alarmas y averías para poder detectar
posibles fallos en el momento de la puesta en marcha del
sistema. Para habilitar el Modo Diagnósticos:
1
Desde el menú de configuración, pulse la tecla ‘
1 ’
para entrar en el menú ‘Opciones de Central’. Primero
aparecerá la pantalla de Idioma.
2
Pulse las teclas ‘
2 /
8 ’ para visualizar las diferentes
opciones hasta que aparezca la pantalla de Modo
Diagnósticos:
6
[Confi]           React.Zumb = En cada alarma punto
>
[… contenido truncado para legibilidad]
```

**[F5]** `ID3000` · *13.3Retardos de módulos* · `MPDT190` p.124 · sim 0.85

```
13.3Retardos de módulos (continuación)

[TABLA EXTRAÍDA]
|  |  | Panel ID3000 | - Ma | nual de | programación | 
----------------------------------------
 |  |  | Nota:Las averías | de | “Equip | o perdido/no | 
 |  |  | responde” s | e s | eñaliza | n de forma | 
 |  |  | inmediata, pe | ro la | s averí | as de niveles | 
 |  |  | analógicos se | reta | rdan c | omo se indica | 
 |  |  | anteriormente | . |  |  | 
 |  |  | Se aconseja utilizar | un re | tardo e | n los eventos | 
 |  |  | de avería y preala | rma | (obsé | rvese que el | 
 |  |  | mismo parámetro es | com | ún para | ambos) para | 
 |  |  | disponer de un tiem | po d | e “ajust | e” del sensor, | 
 |  |  | especialmente de | spu | és de | conectar el | 
 |  |  | sistema. Normalm | ente | , no e | s necesario | 
 |  |  | programar un retard | o de | alarma | a menos que | 
 |  |  | las condiciones esp | ecífi | cas de | la instalación | 
 |  |  | lo requieran. |  |  |  | 
 |  |  | Si se realiza una pru | eba | de sen | sor, se ignora | 
 |  |  | el retardo correspon | dien | te. |  | 
 |  | 13.3 | Retardos de mó | dul | os |  | 
 |  |  | Los retardos de alar | ma y | avería d | e los módulos | 
 |  |  | están programados | de fá | brica d | e la siguiente | s
 |  |  | manera: |  |  |  | e n
 |  |  | a. Alarma |  |  |  | o
 |  |  | (cuando sea apli | cabl | e): | 0 segundos | i
 |  |  |  |  |  | (inmediato) | c a
 |  |  | b. Cortocircuito |  |  |  | d
Si la | supervisión | de | y circuito abierto | : |  | 20 segundos | 
cortocir | cuito está ac | tivada |  |  |  |  | n
(ON), se | recomienda | utilizar | Si se realiza una pru | eba | de sen | sor, se ignora | e
un ret | ardo de alar | ma 1 | el retardo correspon | dien | te. |  | m
 | segundo. |  |  |  |  |  | 
 |  |  | Se aconseja utilizar | un re | tard
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, necesito saber qué modelo de central estás usando y qué indica exactamente en pantalla o en los indicadores LED.

¿Qué modelo de central es (fabricante y modelo concreto) y qué ves en el display o qué LEDs están encendidos?
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

**Razón del judge:** La pregunta es genuinamente ambigua: los fragmentos disponibles cubren múltiples modelos (ID3000, CCD-100, ID50/60) con distintos procedimientos de arranque y error, por lo que sin saber el modelo y los indicadores activos no es posible dar una respuesta útil. El bot pide exactamente los dos datos concretos necesarios (modelo y estado de pantalla/LEDs), lo cual es la conducta esperada 'ask_clarification'. No hace afirmaciones técnicas inventadas, por lo que corpus_faithful y citation_faithful no

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general`):**

Ante "central da error genérico al arrancar", el bot debería pedir clarificación: (1) fabricante y modelo (ID3000, ID50/60, CCD-100, CAD-150/250, Dimension, etc.), (2) mensaje exacto del display o LEDs encendidos, (3) si es la primera puesta en marcha o ya estaba operativa. Idealmente listar familias plausibles dadas las marcas habituales en el corpus.

**Calidad de los chunks:**

- F1 (ID3000) muestra contenido repetitivo: cabeceras de display "Avería Lun 01-May-2000 11:20:07" duplicadas — extracción de pantalla con ruido.
- F3 tiene `[TABLA EXTRAÍDA]` aplicada sobre texto plano de viñetas (procedimiento de actuación), error de extracción.
- F5 `[TABLA EXTRAÍDA]` aplicada sobre notas marginales del manual ID3000 — texto fragmentado por tokens de caracteres ("e n", "o", "i c a d", "n", "e m").
- Cobertura razonable de múltiples modelos (ID3000, CCD-100, ID50/60) lo que justifica clarificación.

**Comparación con bot:**

- Pidió clarificación correctamente (modelo + estado de display/LEDs) — exactamente lo necesario.
- Omisión menor: no listó candidatos plausibles ("¿es ID3000, ID50/60, CCD-100…?") que habrían facilitado la respuesta del técnico.
- No inventó datos.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta y bien acotada. Keyword_pass=False es ruido (faltaban 'error' y 'mensaje', que el bot sí pidió implícitamente con "qué indica en pantalla").
- **Origen del problema:** chunk-extraction (tablas mal aplicadas) + mejorable que el bot proponga candidatos.

---

## am003 — judge dice **PASS ✓** · (3/8)

**Pregunta del técnico:** ¿Cuál es el consumo del ASD?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 0/5 hits · missing: `['asd531', 'asd532', 'asd533', 'asd535', 'cuál']` · **keyword_pass:** `False`

> _Notas YAML: ASD solo no distingue entre 531/532/533/535. Bot debe listar variantes. forbidden_keywords retirado: el substring-match marca como fallo respuestas válidas (ej: 'los 4 operan a 24 VDC pero el consumo varía' — respuesta que SÍ clarifica contenía '24 vdc' y daba falso positivo). El expected_keywords con las 4 variantes + 'cuál' es indicador suficiente: si el bot no nombra las variantes, falla solo._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `unknown` · *Consumo en reposo Consumo en alarma* · `MIE-MP-520rv04` p.32 · sim 0.71

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

**[F2]** `unknown` · *Consumo en reposo Consumo en alarma* · `MIE-MP-520rv04` p.32 · sim 0.71

```
Consumo en reposo
Consumo en alarma (continuación)

Factores de ajuste – El panel emplea un amplificador de potencia de lazo para suministrar la corriente desde baterías. 
Esto supone un consumo extra que debe tenerse en cuenta en los cálculos. Multiplique el consumo en el lazo por 1,5 
para determinar la corriente suministrada por baterías. 
3  Se indican los consumos típicos en reposo y alarma. Revise la documentación del equipos para ver los consumos en 
cada situación y las necesidades de alimentación. Asegúrese que el consumo de todos y del resto de salidas no supera 
el máximo permitido – revise la sección de especificaciones para ver este valor. 
4  Asegúrese que el consumo de todos y del resto de salidas no supera el máximo permitido – revise la sección de 
especificaciones para ver este valor. 
5  Asegúrese de que el consumo total no supera los límites. Revise la sección de especificaciones para estos valores. 
6  La suma de los consumos en reposo y alarma se multiplica por 1.25. Esto se hace para compensar el envejecimiento de 
las baterías.
```

**[F3]** `unknown` · *Lazo 1 Lazo 2 Lazo 3 Lazo 4 Consumo 24V Auxiliar3 (Máximo 0.25 Amps consumo 24V AUX. C.C.) (Máximo 0.25 Amps consumo 24V* · `MIE-MP-520rv04` p.32 · sim 0.70

```
Lazo 1
Lazo 2
Lazo 3
Lazo 4
Consumo 24V Auxiliar3
(Máximo 0.25 Amps consumo 24V
AUX. C.C.)
(Máximo 0.25 Amps consumo 24V
AUX. C.C.) (continuación)

Factores de ajuste – El panel emplea un amplificador de potencia de lazo para suministrar la corriente desde baterías. 
Esto supone un consumo extra que debe tenerse en cuenta en los cálculos. Multiplique el consumo en el lazo por 1,5 
para determinar la corriente suministrada por baterías. 
3  Se indican los consumos típicos en reposo y alarma. Revise la documentación del equipos para ver los consumos en 
cada situación y las necesidades de alimentación. Asegúrese que el consumo de todos y del resto de salidas no supera 
el máximo permitido – revise la sección de especificaciones para ver este valor. 
4  Asegúrese que el consumo de todos y del resto de salidas no supera el máximo permitido – revise la sección de 
especificaciones para ver este valor. 
5  Asegúrese de que el consumo total no supera los límites. Revise la sección de especificaciones para estos valores. 
6  La suma de los consumos en reposo y alarma se multiplica por 1.25. Esto se hace para compensar el envejecimiento de 
las baterías.
```

**[F4]** `unknown` · *2.2.9  SELECTOR DE FUENTE DE ALIMENTACIÓN ACSI* · `VAP1S0x-MU - Manual Usuario VAP rev3_1` p.11 · sim 0.54

```
2.2.9  SELECTOR DE FUENTE DE ALIMENTACIÓN ACSI (continuación)

[TABLA EXTRAÍDA]
El botón | “TEST” | se encuentra situa | do en | la parte inferior | izquierda d | el | equipo. | Pe | rmite
----------------------------------------
comprobar el | correcto | funcionamiento de | todo | s los indicadore | s. Mientra | s s | e mant | en | ga la
pulsación sobre | el botón | “TEST”, se encend | erán | simultáneamente, | todos ellos | , y | se se em | it | irá un
aviso audible. A | l soltar e | l botón, la comprob | ación | finalizará. Durant | e el proces | o | de prueb | a | todos
los controles m | anuales p | ermanecerán inacti | vos. |  |  |  |  |  | 
2.2.7 TAL | K |  |  |  |  |  |  |  | 
Está sit | uado en e | l lateral izquierdo | del m | icrófono de mano | . Permite s | oli | citar el c | an | al de
aviso de evacu | ación por | voz en todas las z | onas | del sistema, o por | las memor | ias | de zona | q | ue se
encuentren sele | ccionada | s, en el caso de co | ntar co | n teclados de exp | ansión. EV | EN | T |  | 
El botón | “EVENT” | (solo disponible en | versi | ón S02) permite el | lanzamien | to | de event | os | .
Véase 3.2.5 |  |  |  |  |  |  |  |  | 
2.2.8 TER | MINADOR | DE BUS ACSI |  |  |  |  |  |  | 
 |  | Ilustración | 3: Selec | tores BUS ACSI |  |  |  |  | 
El selec | tor de ter | minador “EOL” se e | ncue | ntra situado en la | parte trase | ra | del equi | po | en la
zona central. P | ermite la | activación/desactiv | ación | del terminador de | bus. Éste | co | ntrol deb | e | estar
activo cuando e | l equipo o | cupe la última posi | ción e | n el bus ACSI. |  |  |  |  | 
2.2.9 SELE | CTOR DE | FUENTE DE ALIME | NTAC | IÓN ACSI |  |  |  |  | 
El equip | o dispone | de un selector que | perm | ite elegir el origen | de la fuent | e d | e energí | a, |
[… contenido truncado para legibilidad]
```

**[F5]** `unknown` · *d) Dispositivos ACSI* · `ONE500S01-MU - MANUAL DE USUARIO SERIE ONE v2.1` p.21 · sim 0.54

```
d) Dispositivos ACSI

d) Dispositivos ACSI

3.2.3
Selección de modo avanzado
Activando el modo avanzado se consultará al usuario si desea configurar las salidas de
líneas de altavoz en modo A+B o no. Los siguientes apartados explican el proceso que
hará el equipo de forma automática.
a) Líneas de altavoces y zonas. 
El equipo hace una comprobación de las líneas de altavoces para detectar las que se
han instalado, éstas deben conectarse en orden 1-6 ya que cuando el equipo detecta una
línea sin carga o con impedancia superior al rango de medición (600 Ohm), interpreta que
no se instalan ni esa ni las siguientes. 
Para evitar este problema debe instalarse un terminador de línea LDATFL2 para que el
equipo  la  reconozca  como  línea  en  uso.  Todas  las  zonas  detectadas  quedarán
configuradas  con  supervisión  de  línea  activa,  esto  podrá  ajustarse  desde  el  menú
Configuration ->Speaker Lines.
Además, cuando se haya seleccionado el modo A+B, se debe tener en cuenta que
cada zona deberá contar con 2 líneas A y B consecutivas válidas. Por ejemplo, la zona 1
se formaría con las líneas 1 y 2, la zona 2 con las líneas 3 y 4, y la zona 3 con las líneas 5
y 6. Las líneas que queden sueltas en caso de detectar un número impar, quedarán sin
asignar a ninguna zona.
NOTA: con la supervisión de línea activa  no se pueden utilizar  controladores de
volumen, ya que la impedancia de la línea varía según el nivel ajustado y marcaría fallo.
NOTA: los valores de impedancia son medidos por defecto a 19Khz. Serán distintos a
los que se midan con un medidor de impedancia manual que suele medir en 1khz. 
b) Interfaz ECI (Central de detección de Incendios)
Se comprueba qué entradas están conectadas y disponen de terminadores tal como se
especifica  en  el  capítulo  de  conexiones  2.2
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo concreto de ASD estás usando?
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

**Razón del judge:** La pregunta '¿Cuál es el consumo del ASD?' es ambigua: 'ASD' puede referirse a múltiples productos o modelos distintos, y los fragmentos disponibles cubren varios equipos (paneles Dimension DX1e/DX2e/DX4e, repetidores ZXr, etc.) sin que ninguno se identifique explícitamente como 'ASD'. El bot correctamente pide clarificación sobre el modelo concreto antes de responder, lo cual es la conducta esperada (ask_clarification). No hace afirmaciones técnicas inventadas ni cita fragmentos incorrectamente

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general — ASD = Aspirating Smoke Detector`):**

"ASD" se usa como categoría genérica de detectores por aspiración. El bot debería listar candidatos: "¿Te refieres a ASD-531, ASD-532, ASD-533 o ASD-535 (familia de detectores por aspiración Notifier)?". Los consumos varían entre variantes y modos (reposo/alarma). Mejor: añadir que también pueden ser FAAST LT/XM/FLEX o VESDA si el cliente confunde categorías.

**Calidad de los chunks:**

- Brand attribution incorrecta/ausente: F1-F5 marcan `unknown` en lugar de identificar serie (Morley Dimension, VAP, ONE500 — ninguno es realmente "ASD").
- F1 muestra tabla con datos de paneles Dimension (DX1e/DX2e/DX4e) y repetidores ZXr — no relacionados con ASD-531/532/533/535.
- Retrieval **falla**: la query "consumo ASD" no recupera ningún manual de Notifier ASD-531/532/533/535; trae paneles de potencia y unidades de evacuación por voz.
- Esto refuerza la corrección de pedir clarificación: si el bot hubiera respondido con esos chunks habría sido un desastre.

**Comparación con bot:**

- Pidió clarificación correctamente.
- Respuesta muy breve ("¿qué modelo concreto de ASD?") — pasa pero no lista candidatos (531/532/533/535).
- No inventó datos pese al retrieval malo.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta. El bot evita caer en la trampa del retrieval defectuoso. Mejorable: enumerar variantes (ASD-531/532/533/535).
- **Origen del problema:** retrieval (no recupera manuales ASD reales) + metadata (chunks marcados `unknown`) + behavior parcialmente mejorable.

---

## am004 — judge dice **PASS ✓** · (4/8)

**Pregunta del técnico:** ¿La FAAST es compatible con mi central?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 5/5 hits · missing: `[]` · **keyword_pass:** `True`

### Fragmentos que el bot usó (top 5)

**[F1]** `FAAST FLEX` · *38 https://buildings.honeywell.com/gb/en/products/by-brand/morley-ias* · `A05-7030-100_B_ES_Morley FAAST FLEX Addressable` p.47 · sim 0.72

```
38
https://buildings.honeywell.com/gb/en/products/by-brand/morley-ias

38
https://buildings.honeywell.com/gb/en/products/by-brand/morley-ias

FAAST FLEX direccionable Guía de producto
FAAST FLEX
38
https://buildings.honeywell.com/gb/en/products/by-brand/morley-ias
Códigos
de
eventos
Descripción
Códigos
de
eventos
Descripción
66
Antes de la sustitución, la corrección del
aspirador era de 4
67
Antes de la sustitución, la corrección del
aspirador era de 5
68
Antes de la sustitución, la corrección del
aspirador era de 6
69
Tiempo de espera agotado de sustitución
del aspirador
71
Abandonar la configuración pulsando el
botón
72
Abandonar la configuración mediante la
tapa
73
Emparejamiento manual iniciado
74
Emparejamiento de sonido iniciado
75
Conectado por Bluetooth
76
Bluetooth desconectado
77
La aplicación Token by Bluetooth es
incorrecta
78
La aplicación Token by Bluetooth es
correcta
79
El parámetro de flash de datos está fuera
de rango
80
Error de normalización del cierre de la tapa
82
Error de normalización de datos de
memoria flash
83
Protección por subtensión
86
Se ha solicitado el arranque del módulo
87
Incompatibilidad entre versiones de
firmware
90
Se ha solicitado una actualización del
firmware
91
Actualización del firmware completada con
éxito
92
La actualización del firmware ha fallado
debido a un error genérico
93
La actualización del firmware ha fallado
porque no se ha encontrado la unidad USB
94
La actualización del firmware ha fallado
debido a que el paquete de actualización
no es válido
95
La actualización del firmware ha fallado
debido a un error de escritura de la
memoria flash
```

**[F2]** `FAAST-LT` · *HIGH FLOW* · `I56-6574-005_EN-HS-Stand-Alone-FAAST-LT-200-QIG` p.7 · sim 0.65

```
HIGH FLOW (continuación)

[TABLA EXTRAÍDA]
OR ACTION |  | WARNING OR TROUBLE |  |  | COMMENT / ACTION | 
----------------------------------------
L 1/2 ON Red 1 BLINK Green |  | Channel is in alarm (relay is set) |  |  | No delay with default settings | 
 |  | when sensor is polled |  |  | Not in alarm | 
L 1/2 PRE- ON Yellow |  | Channel is in pre-alarm (relay is set) |  |  |  | 
LEVEL ON Yellow |  | Led number indicates sensor alarm lev reached |  |  | el Only numbers 1 – 9 used | 
ATION ON Yellow |  | FAAST LT is in initialization |  |  |  | 
ON Yellow 1 BLINK Yellow |  | Common or multiple faults |  |  |  | 
 |  | Fault delay |  |  | Default = 60s. | 
ON Green |  | FAAST LT is powered |  |  |  | 
FAULT ON Yellow 1 BLINK Yellow |  | Low / high voltage range warning |  |  | Check PSU wiring and voltage. | 
 |  | Power on alert |  |  | Disabled as default | 
L FLOW ON Green ORS 1/2 |  | The chan - Ce - Le - Ri | LED indicates the air flow for a nel: ntre = normal flow ft = flow low; (-20% at extreme) ght = flow high; (+20% at extreme) |  | On 2 channel unit: Upper row = Ch1 Lower row = Ch2 AALLAARRMM | 
OR ACTION |  | WAR | NING OR TROUBLE |  | COMMENT / ACTION | 
W 1 BLINK Yellow ON Yellow |  | Fault Low | delay in progress flow fault |  | Default is 60s; general fault set at end of delay PPRREEAALLAARRMM Check filter; check pipe network for blockages. | 
1 BLINK Yellow 2 BLINKS Yellow OR ON Yellow |  | Sens | or initialization fault 10 |  | Try to restart device. 1 0 Replace faulty sensor. | 
 |  | Sens Air fl | or communication fault 9 ow sensor fault |  | Check sensor addresses and installation; replace sensor. 9 Try to restart device. | 
1 BLINK Yellow 2 BLINKS Yellow |  | Flow | initialization fault 8 |  | Check filter; check pipe network for blockages. Try 8 to
[… contenido truncado para legibilidad]
```

**[F3]** `FAAST XM` · *STORING* · `I56-3836-006_FAAST_XM_8100E_ML` p.58 · sim 0.65

```
STORING (continuación)

[TABLA EXTRAÍDA]
van 15 tot 21 mm. Er w | orde | n teg | elij | kertijd slechts 1 | inlaat en 1 ui | tlaatleiding ge- | ONDERHOUD |  |  |  |  |  |  | 
----------------------------------------
bruikt. Buisnetwerken | kunne | n b | esta | an uit verschill | ende material | en, zoals ABS, | Het enige beno | digde peri | odieke | onderhoud is | vervang | ing | van het f | ilter zodra het
cPVC, PVC, koper of ro de toepassing, maar wo | estvas rdt do | t sta or d | al. e P | De reistijd van h ipeIQ-software b | et verste gaat eperkt tot een | je hangt af van maximum van | filterlichtje gaat 1. Schakel d | branden. e stroom u | Volg d it. | eze procedure | om het f | ilte | r te verva | ngen.
120 seconden. Raadplee configuratie. | g de | lokal | e v | ereisten en de P | ipeIQ-software | voor de juiste | 2. Open het indicators | deurtje aan bedekt. | de rec | hterzijde van | de rook | mel | der, dat de | LED-systeem-
WEBSERVER |  |  |  |  |  |  | 3. Verwijder | de plastic | frontpl | aat die de LED | 's en toe | ts | en bedekt. | 
Het FAAST-systeem is u | itgeru | st m | et e | en webserver di | e wordt gebru | ikt om de con- | 4. Verwijder | de twee sc | hroeve | n waarmee he | t filter in | de | rookmeld | er bevestigd is.
figuratie van de melder De webserverfuncties zi | en de jn o.a | rook .: | me | lder extern te co | ntroleren. |  | 5. Verwijder verwijdere | het filter e n filter). | n verv | ang het door | een nieu | w | filter (vent | ilator stopt bij
• logische interface | voor | exter | ne | controle van sto | ringen, relais, | deeltjesniveau, | 6. Draai de t van het dr | wee schro aaimomen | even ¼ t. (0,7 | slag aan na d Nm (Newton | e eerste meter)). | ind | icatie van | een verhoging
luchtstroom en str | oomt | oevo | er |  |  |  | 7. Plaat
[… contenido truncado para legibilidad]
```

**[F4]** `FAAST LT` · *REARME + PRUEBA No hay acciones. Al pulsarlo durante 2 s, desactiva las sirenas. REARME + PRUEBA + DESACTIVAR* · `I56-6575-005_ES FAAST LT-200 Loop QIG` p.8 · sim 0.65

```
REARME + PRUEBA
No hay acciones.
Al pulsarlo durante 2 s, desactiva las sirenas.
REARME + PRUEBA +
DESACTIVAR (continuación)

D200-102-01
8
I56-6575-005
Salir del modo de mantenimiento
Para salir del modo de mantenimiento, pulse los tres botones de la 
interfaz de usuario del panel frontal PRUEBA, REARME y DESACTIVAR 
simultáneamente durante 2 segundos. 
También puede rearmar la unidad mediante la entrada remota (cuando 
se haya seleccionado el valor predeterminado) o desconectar y volver a 
conectar el dispositivo.
Si no hay actividad en el modo de mantenimiento durante 5 minutos 
(predeterminado), el indicador AVERÍA parpadea en verde durante 15 
segundos y la unidad regresa al estado normal.
BOTÓN
Modo NORMAL
Modo MANTENIMIENTO
REARME
Al pulsarlo durante 2 s, se inicia el
PROCEDIMIENTO DE CONTRASEÑA
para acceder al modo de mantenimiento.
Al pulsarlo durante 2 s, las alarmas enclavadas, las averías y las 
sirenas (relés) se rearman.
El panel controla la alarma. Si la alarma persiste, vuelva a 
establecer inmediatamente después del rearme.
En el modo ANULADO, si se pulsa durante 2 s, la unidad abandona 
el modo ANULADO, pero permanece en el modo 
MANTENIMIENTO.
DESACTIVAR
Sirve para incrementar los dígitos de la
contraseña en el PROCEDIMIENTO DE
CONTRASEÑA.
Si se pulsa durante 2 s, el dispositivo entra en modo ANULADO 
durante 60 minutos (predeterminado).
Los relés de alarma y avería se restablecen. Los sensores de humo 
siguen informando de la alarma y las averías al panel.
(Para salir del modo ANULADO, véase REARME)
PRUEBA
Sirve para confirmar la contraseña en el
PROCEDIMIENTO DE CONTRASEÑA.
Contraseña predeterminada = 3111.
Al pulsarlo durante 2 s y soltarlo, ambos sensores simulan una 
alarma
Al pulsarlo durante 4 s y soltarlo, el sensor n.º 1 simula una alarma
Al
[… contenido truncado para legibilidad]
```

**[F5]** `FAAST FLEX` · *Descripción* · `A05-7030-100_B_ES_Morley FAAST FLEX Addressable` p.46 · sim 0.72

```
Descripción (continuación)

[TABLA EXTRAÍDA]
Códigos de eventos | Descripción | Códigos de eventos | Descripción
----------------------------------------
66 | Antesdelasustitución,lacorreccióndel aspiradorerade4 |  | 
67 | Antesdelasustitución,lacorreccióndel aspiradorerade5 |  | 
68 | Antesdelasustitución,lacorreccióndel aspiradorerade6 |  | 
69 | Tiempodeesperaagotadodesustitución delaspirador |  | 
71 | Abandonarlaconfiguraciónpulsandoel botón |  | 
72 | Abandonarlaconfiguraciónmediantela tapa |  | 
73 | Emparejamientomanualiniciado |  | 
74 | Emparejamientodesonidoiniciado |  | 
75 | ConectadoporBluetooth |  | 
76 | Bluetoothdesconectado |  | 
77 | LaaplicaciónTokenbyBluetoothes incorrecta |  | 
78 | LaaplicaciónTokenbyBluetoothes correcta |  | 
79 | Elparámetrodeflashdedatosestáfuera derango |  | 
80 | Errordenormalizacióndelcierredelatapa |  | 
82 | Errordenormalizacióndedatosde memoriaflash |  | 
83 | Protecciónporsubtensión |  | 
86 | Sehasolicitadoelarranquedelmódulo |  | 
87 | Incompatibilidadentreversionesde firmware |  | 
90 | Sehasolicitadounaactualizacióndel firmware |  | 
91 | Actualizacióndelfirmwarecompletadacon éxito |  | 
92 | Laactualizacióndelfirmwarehafallado debidoaunerrorgenérico |  | 
93 | Laactualizacióndelfirmwarehafallado porquenosehaencontradolaunidadUSB |  | 
94 | Laactualizacióndelfirmwarehafallado debidoaqueelpaquetedeactualización noesválido |  | 
95 | Laactualizacióndelfirmwarehafallado debidoaunerrordeescrituradela memoriaflash |  |
```

### Respuesta del bot

```
Para responderte con precisión, necesito saber dos cosas:

1. **¿Qué modelo de FAAST tienes instalado?** (por ejemplo, FAAST LT, FAAST XM, FAAST FLEX, u otro)
2. **¿Qué modelo de central tienes?** (fabricante y referencia exacta)

La compatibilidad depende del modelo concreto de detector de aspiración y del tipo de central (convencional, analógica direccionable, protocolo específico). Con esos datos puedo buscarte la información correcta.
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

**Razón del judge:** La pregunta '¿La FAAST es compatible con mi central?' es ambigua en dos dimensiones: no especifica el modelo de FAAST (hay al menos FAAST LT, FAAST FLEX, FAAST XM en el corpus) ni el modelo/fabricante de la central. El bot pide exactamente esos dos datos concretos antes de responder, lo cual es la conducta esperada (ask_clarification). No hace afirmaciones técnicas inventadas, no cita fragmentos incorrectamente, y la acción solicitada al técnico es clara y accionable.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general — familia FAAST de Honeywell/Notifier/Morley`):**

"FAAST" es genérico para detectores por aspiración Honeywell/Morley. El bot debería pedir: (1) modelo concreto FAAST — **FAAST LT (LT-200)**, **FAAST FLEX direccionable** o **FAAST XM (8100E)**; y (2) fabricante/modelo de la central. La compatibilidad depende de si es stand-alone (FAAST LT-200), de lazo direccionable (FLEX, LT Loop) o por relés (FAAST XM). El bot acierta exactamente.

**Calidad de los chunks:**

- F1 y F5 son del mismo manual FAAST FLEX (A05-7030-100) con códigos de evento y tablas duplicadas — **chunk duplication** sistémica.
- F3 está en **neerlandés** (FAAST XM 8100E ML — manual multilenguaje sin filtrar idioma).
- F2 está en **inglés** (FAAST LT-200 QIG en EN).
- F5 tiene `[TABLA EXTRAÍDA]` con texto pegado sin espacios ("Antesdelasustitución,lacorreccióndel").
- Retrieval mezcla 3 familias FAAST + dos idiomas, justificando totalmente la clarificación.

**Comparación con bot:**

- Pidió clarificación **listando candidatos** (FAAST LT, FAAST XM, FAAST FLEX) — esto es lo ideal según los patrones de la categoría.
- Pidió también modelo de central — correcto.
- No inventó nada.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Respuesta modelo de la categoría: ambigüedad doble (FAAST + central), bot pide ambas y enumera candidatos plausibles. Patrón a replicar en am001/am006.
- **Origen del problema:** ninguno en la respuesta. Issues laterales: duplicación de chunks + idioma mezclado.

---

## am005 — judge dice **PASS ✓** · (5/8)

**Pregunta del técnico:** ¿Cómo reseteo el panel?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 2/3 hits · missing: `['fabricante']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `CAD-250` · *INSTALACION (Menú principal) > PANEL (Submenú)* · `CAD-250-MC-380-es` p.89 · sim 0.67

```
INSTALACION (Menú principal) > PANEL (Submenú)

INSTALACION (Menú principal) > PANEL (Submenú)

89
ESP
11.3.	CONFIGURACIONES DE PANEL
Desde este submenú es posible ajustar algunos modos útiles en el 
proceso de puesta en marcha. Para acceder pulse:
INSTALACION (Menú principal) > PANEL (Submenú)
Menú Principal
SubMenú
Vista Principal
⚠AVISO! Las opciones disponibles en este menú sólo deben ser 
empleadas por personal entrenado. En general todas ellas deben 
permanecer activas, la desconexión situará el panel fuera del ámbito 
de cumplimiento de la normativa EN54-2., lea detenidamente cada 
caso. 
Durante el proceso de puesta en marcha o durante los trabajos de 
resolución de problemas, puede estar justificada la desconexión 
parcial o total de estos elementos. Tome las medidas preventivas que 
correspondan si el sistema ya está activo en el momento de utilizar 
este menú.
La desconexión de señales obligatorias provocarán la señalización 
correspondiente de anulación en los indicadores del panel. Recuerde 
que se trata de una configuración manual, recupere la configuración 
correcta tan pronto como finalice los trabajos. Informe al responsable 
del sistema de los  cambios en este menú y sus consecuencias.
El menú de panel pemite configurar los siguientes elementos:
Habilitar relés. La desconexión de este interruptor, color gris, 
impedirá la activación de todas las salidas de relé, central y 
módulos de control del sistema. Normalmente debe estar activo.
Habilitar sirenas. La desconexión de este interruptor, color gris, 
impedirá la activación de todas las salidas de sirena, de placa 
base de central y módulos de control configurados como sirena 
y sirenas y dispositivos visuales del sistema. Normalmente debe 
estar activo. La desconexión permanente puede contravenir los
[… contenido truncado para legibilidad]
```

**[F2]** `unknown` · *Paso 12 La actualización del software del panel puede durar unos minutos. Cuando finalice, aparecerá la siguiente pantal* · `MIE-MP-520rv04` p.85 · sim 0.68

```
Paso 12
La actualización del software del panel puede durar unos minutos. Cuando finalice, aparecerá la
siguiente pantalla:

Paso 12
La actualización del software del panel puede durar unos minutos. Cuando finalice, aparecerá la
siguiente pantalla:

Serie Dimension Series 

MorleyIAS 

Manual de Configuración 
Documento No.MIE-MP-520 
Página 85 de 88 

Paso 12 
La actualización del software del panel puede durar unos minutos. Cuando finalice, aparecerá la 
siguiente pantalla:  

NOTA: Si el programa indica que no se puede conectar al panel de control, compruebe que el ajuste 
del puerto de comunicaciones sea el correcto y que los conectores de bloqueo de memoria y flash 
estén en las posiciones correctas. Desconecte y vuelva a conectar el panel de control y vuelva a 
intentarlo de nuevo.  

Si se indica que el proceso de verificación ha fallado, repita los pasos 11 y 12. 

Paso 13 
Desconecte el panel de control y coloque el conector ‘Flash’ (J1) a la posición de anulado (DISABLE).  

Paso 14 
Conecte de nuevo el panel de control.  

Paso 15 
Ahora es necesario realizar un borrado de los ajustes del panel desde el menú de sistema antes de 
restaurarlos desde el programa de configuración de la DX: 

(i) Pulse cualquier tecla para entra en los menús. Introduzca la clave de nivel 3 cuando se le solicite:  

ACCESO A MENUS RESTRINGIDO
Introd.Clave Nivel 2/3 ,
presione

(ii) En el siguiente menú, pulse 1 para entrar en el menú de Configuración: 

[S1]
1.Configuración
2.Prueba 3.Reloj
4.Anular/Habilitar
5.Ver

(iii) En el siguiente menú, pulse 7 para opciones avanzadas:  

[S1 CONFG] 1.Opciones Panel
2.Sal. placa
3. Lazo(s)
4:Zonas
5:Salir
:Más
```

**[F3]** `CCD-100` · *4.4.2- Conexión de salida 24VCC reseteables* · `55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT` p.17 · sim 0.80

```
4.4.2- Conexión de salida 24VCC reseteables

15
ES
4.4- Conexionado de salida auxiliar 24VCC
Las centrales convencionales disponen de 2 salidas de 24V auxiliares, una de ellas 
reseteable. La corriente total de las 2 salidas en de 500 mA y esta protegida por un 
fusible común.
4.4.1- Conexión de salida auxiliar 24VCC
La salida de 24VCC está destinada a alimentar los elementos exteriores auxiliares 
que precisan alimentación, no se recomienda utilizar esta salida para suministrar 
alimentación a elementos que tengan consumo en modo reposo.
4.4.2- Conexión de salida 24VCC reseteables
La salida de 24VCC reseteable esta destinada a alimentar dispositivos que precisan 
ser reseteados desde la central (barrera infrarroja). Esta salida tiene 24V en reposo y 
cuando se resetea la central, los 24V se desconectan durante 3 segundos.
4.5- Conexión de salida de relé libre tensión
Las centrales convencionales disponen de un relé de avería y un relé de alarma. Son 
salidas que actúan cuando existe una alarma o una avería. La corriente máxima de 
los relés es de 2A.
El relé de avería es energizado, con lo cual, en caso de avería conmutará, señalizando 
la correspondiente avería.


[TABLA EXTRAÍDA]
4.4- | Conexiona | do | de s | alid | a a | uxili | ar 24VC | C
----------------------------------------
Las centrales co | nvencionales di | spon | en de | 2 sali | das | de 24V | auxiliares, | una de ellas
reseteable. La c | orriente total de | las 2 | salid | as en | de | 500 mA | y esta prote | gida por un
fusible común. |  |  |  |  |  |  |  | 
4.4.1- Conex | ión de salida | aux | iliar 2 | 4VCC |  |  |  | 
La salida de 24 | VCC está destin | ada | a alim | entar | los | elemen | tos exteriore | s auxiliares
que precisan ali | mentación, no | se re | comi | enda u | tiliz | ar esta | sal
[… contenido truncado para legibilidad]
```

**[F4]** `CCD-100` · *4.4- Conexionado de salida auxiliar 24VCC* · `55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT` p.17 · sim 0.80

```
4.4- Conexionado de salida auxiliar 24VCC

15
ES
4.4- Conexionado de salida auxiliar 24VCC
Las centrales convencionales disponen de 2 salidas de 24V auxiliares, una de ellas 
reseteable. La corriente total de las 2 salidas en de 500 mA y esta protegida por un 
fusible común.
4.4.1- Conexión de salida auxiliar 24VCC
La salida de 24VCC está destinada a alimentar los elementos exteriores auxiliares 
que precisan alimentación, no se recomienda utilizar esta salida para suministrar 
alimentación a elementos que tengan consumo en modo reposo.
4.4.2- Conexión de salida 24VCC reseteables
La salida de 24VCC reseteable esta destinada a alimentar dispositivos que precisan 
ser reseteados desde la central (barrera infrarroja). Esta salida tiene 24V en reposo y 
cuando se resetea la central, los 24V se desconectan durante 3 segundos.
4.5- Conexión de salida de relé libre tensión
Las centrales convencionales disponen de un relé de avería y un relé de alarma. Son 
salidas que actúan cuando existe una alarma o una avería. La corriente máxima de 
los relés es de 2A.
El relé de avería es energizado, con lo cual, en caso de avería conmutará, señalizando 
la correspondiente avería.


[TABLA EXTRAÍDA]
4.4- | Conexiona | do | de s | alid | a a | uxili | ar 24VC | C
----------------------------------------
Las centrales co | nvencionales di | spon | en de | 2 sali | das | de 24V | auxiliares, | una de ellas
reseteable. La c | orriente total de | las 2 | salid | as en | de | 500 mA | y esta prote | gida por un
fusible común. |  |  |  |  |  |  |  | 
4.4.1- Conex | ión de salida | aux | iliar 2 | 4VCC |  |  |  | 
La salida de 24 | VCC está destin | ada | a alim | entar | los | elemen | tos exteriore | s auxiliares
que precisan ali | mentación, no | se re | comi | enda u | tiliz | ar esta | salid
[… contenido truncado para legibilidad]
```

**[F5]** `CCD-100` · *4.4.1- Conexión de salida auxiliar 24VCC* · `55310021-Manual-Centrales-Convencionales-CCD-100-ES_GB_FR_IT` p.17 · sim 0.80

```
4.4.1- Conexión de salida auxiliar 24VCC

15
ES
4.4- Conexionado de salida auxiliar 24VCC
Las centrales convencionales disponen de 2 salidas de 24V auxiliares, una de ellas 
reseteable. La corriente total de las 2 salidas en de 500 mA y esta protegida por un 
fusible común.
4.4.1- Conexión de salida auxiliar 24VCC
La salida de 24VCC está destinada a alimentar los elementos exteriores auxiliares 
que precisan alimentación, no se recomienda utilizar esta salida para suministrar 
alimentación a elementos que tengan consumo en modo reposo.
4.4.2- Conexión de salida 24VCC reseteables
La salida de 24VCC reseteable esta destinada a alimentar dispositivos que precisan 
ser reseteados desde la central (barrera infrarroja). Esta salida tiene 24V en reposo y 
cuando se resetea la central, los 24V se desconectan durante 3 segundos.
4.5- Conexión de salida de relé libre tensión
Las centrales convencionales disponen de un relé de avería y un relé de alarma. Son 
salidas que actúan cuando existe una alarma o una avería. La corriente máxima de 
los relés es de 2A.
El relé de avería es energizado, con lo cual, en caso de avería conmutará, señalizando 
la correspondiente avería.


[TABLA EXTRAÍDA]
4.4- | Conexiona | do | de s | alid | a a | uxili | ar 24VC | C
----------------------------------------
Las centrales co | nvencionales di | spon | en de | 2 sali | das | de 24V | auxiliares, | una de ellas
reseteable. La c | orriente total de | las 2 | salid | as en | de | 500 mA | y esta prote | gida por un
fusible común. |  |  |  |  |  |  |  | 
4.4.1- Conex | ión de salida | aux | iliar 2 | 4VCC |  |  |  | 
La salida de 24 | VCC está destin | ada | a alim | entar | los | elemen | tos exteriore | s auxiliares
que precisan ali | mentación, no | se re | comi | enda u | tiliz | ar esta | salida
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo de panel estás usando y qué tipo de reset necesitas (reset tras alarma, reset de fábrica/configuración, o reset de la salida auxiliar)?

El procedimiento varía según el equipo y el tipo de operación.
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

**Razón del judge:** La pregunta '¿Cómo reseteo el panel?' es ambigua: los fragmentos disponibles cubren al menos tres productos distintos (CAD-250, CCD-100, MorleyIAS Dimension) con procedimientos de reset diferentes, y el término 'reset' puede referirse a rearme tras alarma (V2), reset de configuración de fábrica (F2), o reset de salida auxiliar (F3/F4). El bot correctamente pide UN detalle concreto (modelo + tipo de reset) antes de responder, lo cual coincide exactamente con la conducta esperada 'ask_clarificatio

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general`):**

"Reseteo del panel" es triple-ambiguo: (1) modelo de central, (2) tipo de reset (rearme tras alarma, factory reset/borrado config, reset de salida 24V reseteable a sensores 4-hilos), (3) nivel de acceso (nivel 2 usuario vs nivel 3 instalador). El bot debería listar candidatos de marca/serie habituales (CAD-150/250, CCD-100, ID3000, ID50/60, Dimension, Notifier System 5000) y enumerar los 3 tipos de reset.

**Calidad de los chunks:**

- F3, F4 y F5 son **el mismo chunk del CCD-100 página 17** repetido tres veces con headers ligeramente distintos (4.4 / 4.4.1 / 4.4.2) — **duplicación masiva** de chunks; el retrieval llena 3/5 slots con el mismo contenido.
- F3-F5 tienen `[TABLA EXTRAÍDA]` mal aplicada sobre texto plano del epígrafe 4.4 (no es una tabla real).
- F2 marcado `unknown` cuando es claramente Morley Dimension (MIE-MP-520) — metadata pobre.
- Sólo F1 (CAD-250) habla específicamente de configuración de panel.

**Comparación con bot:**

- Pidió clarificación correctamente desglosando los 3 tipos de reset (alarma / fábrica / salida auxiliar) — útil y didáctico.
- Omisión: no enumeró candidatos de modelo plausibles.
- No inventó datos.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Buena clarificación con enumeración de tipos de reset (caso poco común y valioso). Pierde puntos por no listar modelos candidatos.
- **Origen del problema:** retrieval (duplicación masiva CCD-100) + metadata (`unknown` en Dimension) + behavior parcialmente mejorable.

---

## am006 — judge dice **PASS ✓** · (6/8)

**Pregunta del técnico:** Necesito añadir un detector al lazo 2 de la ID

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 0/5 hits · missing: `['id1000', 'id2000', 'id3000', 'id50', 'cuál']` · **keyword_pass:** `False`

> _Notas YAML: ID es ambiguo entre ID1000/2000/3000/50/60._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `INSPIRE` · *Disponible     Seleccionado    Configurado   Ocupado    No Disponible* · `4188-1124-ES issue 6_01-2026_To` p.27 · sim 0.81

```
Disponible     Seleccionado    Configurado   Ocupado    No Disponible

Disponible     Seleccionado    Configurado   Ocupado    No Disponible

27
Programa de configuración de CLSS – Guía técnico
AGREGAR DISPOSITIVOS
Puede agregar manualmente dispositivos de detectores y módulos a cada circuito de lazo si planifica un sistema o edita un sistema 
existente para adaptarse a dispositivos nuevos o cambiados. Asegúrese de que la dirección elegida para un dispositivo sea la misma 
que la dirección de hardware establecida en el dispositivo. Si ya se han localizado DISPOSITIVOS, vaya a EDITAR DISPOSITIVOS.
1 Seleccione un lazo y, a continuación  ⊕ Añadir dispositivos.
2 Busque la lista de dispositivos y seleccione un detector o un módulo.    
3 Seleccione un tipo de dispositivo e insértelo en un cuadro de dirección disponible del rango 1 al 159 y aplique el dispositivo a la 
dirección. El color de fondo del cuadro de dirección determinará su estado:

Disponible     Seleccionado    Configurado   Ocupado    No Disponible

 La casilla de dirección 1 está ocupada, con 2, 3 y 5 disponibles y 4 seleccionada.

Puede deseleccionar una dirección haciendo clic de nuevo en la ubicación.
La dirección seleccionada debe ser la misma que la que se establece en los selectores de 
direccionamiento del dispositivo.
4 Repita los pasos 03 a 04 para agregar más dispositivos al lazo.
5 Seleccione FINALIZAR  cuando se añadan todos los dispositivos a un lazo.
Consejo 1: Puede seleccionar un tipo de detector o módulo y asignarlo a varias direcciones en el lazo. Para ello, pulse el botón Control 
del Pc, haga clic en cada casilla de dirección y, a continuación, seleccione un dispositivo. Para deseleccionar, haga clic en la misma 
dirección del lazo. 
Consejo 2: Puede seleccionar varias direcciones secuenc
[… contenido truncado para legibilidad]
```

**[F2]** `CAD-250` · *2.1.	 LAZOS Y DISPOSITIVOS* · `CAD-250-MS-416-es` p.12 · sim 0.71

```
2.1.	 LAZOS Y DISPOSITIVOS

ESP
12
2.	 ARQUITECTURA DEL SISTEMA VESTA.
VESTA es un un potente sistema de detección y alarma de incendios 
analógico direccionable basado en centrales CAD-250. Esta es una 
central analógica con características de configuración y funcionales 
avanzadas, diseñada para funcionar con los sensores analógicos, 
módulos, y pulsadores direccionables DETNOV. Su concepción 
modular permite al usuario disponer de un sistema extremadamente 
potente y completamente flexible.
2.1.	 LAZOS Y DISPOSITIVOS 
Los elementos de detección automática, los elementos de detección 
manual, pulsadores, modulos de monitoreo, o los elementos de salida 
como sirenas o módulos de control, son los dispositivos que  se 
conectan a las centrales CAD-250 en lazo cerrado.
La central admite el funcionamiento en lazo abierto, sin embargo, no 
es recomendable el uso de esta topología donde una únca incidencia 
en las líneas de transmisión pueden provocar la pérdida de protección 
en áreas significativamente grandes.
Las normas de diseño y de producto o locales en Europa exigen 
el uso de sistemas de lazo cerrado. Verifique los reqisitos de su 
reglamentación local
Cada lazo puede soportar hasta 250 dispositivos diferentes y 250 
direcciones.
Tenga en cuenta que hay dispositivos que emplean más de una 
dirección. Acuda al APENDICE 1 al final del capítulo para revisar los 
tipos de dispositivos disponibles, el número de direcciones que usan 
en el lazo y su consumo.
2.2.	 	 ENTRADAS DE FUEGO Y AUXILIARES
La misión principal del panel de detección es la identificación de un 
posible incendio, Estos son los detectores automáticos, los pulsadores 
de alarma y los módulos de monitoreo configurados para este fin.
Algunos módulos de monitoreo tienen como misión la supervisión de 
señal
[… contenido truncado para legibilidad]
```

**[F3]** `CAD-250` · *11.4.	 CONFIGURACIONES DE LAZO* · `CAD-250-MC-380-es` p.91 · sim 0.75

```
11.4.	 CONFIGURACIONES DE LAZO

11.4.	 CONFIGURACIONES DE LAZO

91
ESP
11.4.	 CONFIGURACIONES DE LAZO
Desde este submenú es posible ajustar algunas funciones de lazo. 
Para acceder pulse:
INSTALACION (Menú principal) > PANEL (Submenú)
Menú Principal
SubMenú
Vista Principal
Este menú ofrece las siguientes opciones de configuración:
Parpadeo Led: El pulso intermitente de los indicadores led es una 
muestra de los intercambios de información entre la central y el detector. 
En determinados usos, por ejmeplo en aquellos en los que duermen 
personas, la luminosidad de los indicadores led puede resultar muy 
molesto para el residente. Al mover este interruptor a la posición apagado, 
en color gris, esta indicacción de exploración no se hará. Normalmente 
su posición es activo, en color verde.
Notificación por suciedad. El paso del tiempo acumulará suciedad 
en la cámara de los detectores de humo. Esto puede suceder a mayor 
o menor velocidad en función del entorno de trabajo. 
La central CAD-250 dispone de un procedimiento de identificación 
de cámara sucia. El algorítmo de control evalúa la evolución del 
valor de cámara y determina según esta si debe activar una alerta 
de mantenimiento. Es posible deshabilitar esta función desactivando 
el interruptor de notificación de suciedad. Su configuración normal es 
activado, en color verde.
Notificación no configurado. Al hacer una exploración mediante 
la función AUTOBUSQUEDA del menú de lazo, es posible que a algún 
dispositivo no le haya sido configurada la dirección. esta función permite 
identificar la existencia de dispositivos sin configuración mientras el 
interruptor esté activo, en verde. la posición por defecto del interruptor 
es activo, en verde. Identifique los dispositivos y configurelos con ayuda 
del programador P
[… contenido truncado para legibilidad]
```

**[F4]** `CAD-250` · *INSTALACION (Menú principal) > PANEL (Submenú)* · `CAD-250-MC-380-es` p.91 · sim 0.73

```
INSTALACION (Menú principal) > PANEL (Submenú)

INSTALACION (Menú principal) > PANEL (Submenú)

91
ESP
11.4.	 CONFIGURACIONES DE LAZO
Desde este submenú es posible ajustar algunas funciones de lazo. 
Para acceder pulse:
INSTALACION (Menú principal) > PANEL (Submenú)
Menú Principal
SubMenú
Vista Principal
Este menú ofrece las siguientes opciones de configuración:
Parpadeo Led: El pulso intermitente de los indicadores led es una 
muestra de los intercambios de información entre la central y el detector. 
En determinados usos, por ejmeplo en aquellos en los que duermen 
personas, la luminosidad de los indicadores led puede resultar muy 
molesto para el residente. Al mover este interruptor a la posición apagado, 
en color gris, esta indicacción de exploración no se hará. Normalmente 
su posición es activo, en color verde.
Notificación por suciedad. El paso del tiempo acumulará suciedad 
en la cámara de los detectores de humo. Esto puede suceder a mayor 
o menor velocidad en función del entorno de trabajo. 
La central CAD-250 dispone de un procedimiento de identificación 
de cámara sucia. El algorítmo de control evalúa la evolución del 
valor de cámara y determina según esta si debe activar una alerta 
de mantenimiento. Es posible deshabilitar esta función desactivando 
el interruptor de notificación de suciedad. Su configuración normal es 
activado, en color verde.
Notificación no configurado. Al hacer una exploración mediante 
la función AUTOBUSQUEDA del menú de lazo, es posible que a algún 
dispositivo no le haya sido configurada la dirección. esta función permite 
identificar la existencia de dispositivos sin configuración mientras el 
interruptor esté activo, en verde. la posición por defecto del interruptor 
es activo, en verde. Identifique los dispositivos y configure
[… contenido truncado para legibilidad]
```

**[F5]** `CAD-250` · *4.16.5. Ajustes especiales de lazo* · `CAD-250-MS-416-es` p.38 · sim 0.73

```
4.16.5.
Ajustes especiales de lazo

ESP
38
4.16.5.	
Ajustes especiales de lazo
Este menú ofrece las siguientes opciones de configuración:
Parpadeo Led: El pulso intermitente de los indicadores led es una 
muestra de los intercambios de información entre la central y el 
detector. En determinados usos, por ejmeplo en aquellos en los que 
duermen personas, la luminosidad de los indicadores led puede 
resultar muy molesto para el residente. Al mover este interruptor a la 
posición apagado, en color gris, esta indicacción de exploración no se 
hará. Normalmente su posición es activo, en color verde.
Notificación por suciedad. El paso del tiempo acumulará suciedad 
en la cámara de los detectores de humo. Esto puede suceder a mayor 
o menor velocidad en función del entorno de trabajo. 
La central CAD-250 dispone de un procedimiento de identificación 
de cámara sucia. El algorítmo de control evalúa la evolución del 
valor de cámara y determina según esta si debe activar una alerta 
de mantenimiento. Es posible deshabilitar esta función desactivando 
el interruptor de notificación de suciedad. Su configuración normal es 
activado, en color verde.
Notificación no configurado. Al hacer una exploración mediante 
la función AUTOBUSQUEDA del menú de lazo, es posible que a algún 
dispositivo no le haya sido configurada la dirección. esta función permite 
identificar la existencia de dispositivos sin configuración mientras el 
interruptor esté activo, en verde. la posición por defecto del interruptor 
es activo, en verde. Identifique los dispositivos y configurelos con ayuda 
del programador PGD-200 o mediante la función PROGRAMACION DE 
UNA DIRECCION del menú LAZO.
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo concreto de central "ID" estás usando? Necesito el modelo exacto (puedes leerlo en la etiqueta del panel) para darte el procedimiento correcto.
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

**Razón del judge:** La pregunta menciona 'la ID' sin especificar el modelo exacto (ID3000, ID3K, etc.), lo que es ambiguo dado que los fragmentos disponibles cubren al menos dos productos distintos (INSPIRE/CLSS y CAD-250). El bot pide correctamente el modelo concreto de la central antes de responder, lo cual es la conducta esperada (ask_clarification). No hace afirmaciones técnicas inventadas y la aclaración solicitada es el único detalle necesario para dar el procedimiento correcto.

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general — familia Notifier ID`):**

"La ID" es ambigua: la familia Notifier ID incluye **ID3000**, **ID50** e **ID60** (las series ID1000/ID2000 están descatalogadas pero hay manuales). Procedimiento de añadir detector difiere entre ID50/60 (programación local desde teclado) e ID3000 (consola PC NRX/PCMag). El bot debería listar las series candidatas y, una vez identificada, preguntar protocolo (CLIP vs OPAL/Advanced) si aplica.

**Calidad de los chunks:**

- **Retrieval crítico fallido**: la pregunta menciona "ID" pero los chunks recuperados son **INSPIRE/CLSS** (4188-1124) y **CAD-250** (Detnov) — ninguno es Notifier ID. Esto es brand-attribution wrong / retrieval drift.
- F2-F5 son todos CAD-250 (Detnov VESTA) — el bot no tiene chunks ID3000/ID50/60 disponibles aunque existen en el corpus.
- Si el bot hubiera intentado responder, lo habría hecho con manuales de **OTRA marca** (Detnov vs Notifier).

**Comparación con bot:**

- Pidió clarificación — comportamiento correcto, especialmente crítico aquí porque los chunks son de marca equivocada.
- Omisión grave: no listó las series ID candidatas (ID3000, ID50, ID60), tampoco mencionó que los chunks disponibles no son ID.
- No cayó en la trampa de responder con CAD-250 como si fuera ID — punto positivo.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta y crítica: con retrieval defectuoso (chunks de marca distinta), pedir clarificación es la única respuesta segura. Si el judge fuera estricto sobre helpful podría rebajar nota por no enumerar candidatos, pero behavior_match es correcto.
- **Origen del problema:** **retrieval grave** (no recupera Notifier ID, recupera Detnov CAD-250 e INSPIRE) — el bot lo compensa con cautela.

---

## am007 — judge dice **PASS ✓** · (7/8)

**Pregunta del técnico:** ¿Cómo se cablea la VESDA?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 3/7 hits · missing: `['vep', 'veu', 'vea', 'cuál']` · **keyword_pass:** `False`
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `VESDA VLF-500` · *2.7 Conexiones del cableado* · `11370_17_VESDA_VLF-500_Product_Guide_A4_Spanish_lores` p.18 · sim 0.80

```
2.7
Conexiones del cableado

VESDA VLF-500 Guía del producto
VESDA by Xtralis
12
www.xtralis.com
2.7
Conexiones del cableado
Precaución: Deben tomarse precauciones contra la descarga electrostática antes de retirar la tapa frontal
del detector, de lo contrario la unidad podría dañarse.
2.7.1
Requisitos de cableado del detector
Los terminales de tipo rosca ubicados en la tarjeta de terminación dentro del VESDA VLFF aceptan tamaños
de cable desde 0,2 mm2 hasta 2,5 mm2 (30-12 AWG).
Consulte Información sobre códigos y estándares para la detección de humo por muestreo de aire en la
páginaiii para conocer los requisitos específicos de los códigos.
Consulte el Manual de diseño del sistema de VESDA para obtener detalles acerca del cableado.
Para alcanzar el bloque del terminal, abra la puerta de acceso de servicio sobre el terreno, consulte Controles
e indicadores en la página 33 y desatornille los tornillos de fijación de la tapa frontal. Despegue y balancee
hacia abajo la tapa frontal. El bloque del terminal se encuentra a la derecha del detector.
Leyenda
A
Bloque del terminal, conectores 1-20
Figura 2-8: Bloque del terminal


[TABLA EXTRAÍDA]
A: Bloquedelterminal,conectores1-20
```

**[F2]** `VESDA VLF-250` · *2.7 Conexiones del cableado* · `11369_22_VESDA_VLF-250_Product_Guide_A4_Spanish_lores` p.18 · sim 0.80

```
2.7
Conexiones del cableado

VESDA VLF-250 Guía del producto
VESDA by Xtralis
12
www.xtralis.com
2.7
Conexiones del cableado
Precaución: Deben tomarse precauciones contra la descarga electrostática antes de retirar la tapa frontal
del detector, de lo contrario la unidad podría dañarse.
2.7.1
Requisitos de cableado del detector
Los terminales de tipo rosca ubicados en la tarjeta de terminación dentro del VESDA VLFF aceptan tamaños
de cable desde 0,2 mm2 hasta 2,5 mm2 (30-12 AWG).
Consulte Información sobre códigos y estándares para la detección de humo por muestreo de aire en la
páginaiii para conocer los requisitos específicos de los códigos.
Consulte el Manual de diseño del sistema de VESDA para obtener detalles acerca del cableado.
Para alcanzar el bloque del terminal, abra la puerta de acceso de servicio sobre el terreno, consulte Controles
e indicadores en la página 33 y desatornille los tornillos de fijación de la tapa frontal. Despegue y balancee
hacia abajo la tapa frontal. El bloque del terminal se encuentra a la derecha del detector.
Leyenda
A
Bloque del terminal, conectores 1-20
Figura 2-8: Bloque del terminal


[TABLA EXTRAÍDA]
A: Bloquedelterminal,conectores1-20
```

**[F3]** `VESDA-E VEU` · *Nota: Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E Communications Guide).* · `33978_12_VESDA-E_VEU-A00_Product_Guide_A4_Spanish_lores` p.44 · sim 0.80

```
Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

VESDA-E VEU-A00 Guía del producto
38
www.xtralis.com
4.3.5
VESDAnet
VESDAnet es una red de comunicación de datos bidireccional entre los dispositivos de VESDA-E
conectados. La conectividad de VESDAnet está disponible en el detector VEU-A00. Consulte la sección 2.6
para obtener más información.
Es recomendable utilizar cables de par trenzado RS 485 (Belden 9841 - 120 ohmios) para incluir los
dispositivos en la red.
Los cables de red finalizan en los terminales A y B de VESDAnet. El cableado de un dispositivo VESDA-E se
introduce en el detector en un terminal y se conecta a otro dispositivo en VESDAnet desde el otro terminal.
Notas:
l La polaridad de los cables de datos debe mantenerse en toda la red.
l Para que el detector pueda detectar fallos de conexión a tierra en el cableado de VESDAnet, el terminal
de referencia a tierra (Figura 4-33) debe conectarse a una toma a tierra local.
A+
A-
B-
Pantalla
Módulo 1
Módulo 2
Módulo 3
Módulo 5
Módulo 4
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
(VESDA-E VEU)
Figura 4-35: Ejemplo de circuito cerrado de la red VESDAnet
El detector VESDA-E VEU-A00 se envía con los terminales A y B en circuito de VESDAnet. Retire las
conexiones A y B antes de conectar el detector a VESDAnet. Si el detector no debe conectarse a la red con
otros dispositivos, no retire las conexiones A y B.
Pantalla
A-
A+
Pantalla
B-
B+
Figura 4-36: Circuito cerrado para detectores independientes con función de VESDAnet
Nota:
Para obtener más información,
[… contenido truncado para legibilidad]
```

**[F4]** `VESDA-E VEP-A00` · *Nota: Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E Communications Guide).* · `33976_13_VESDA-E_VEP-A00-P_Product_Guide_A4_Spanish_lores` p.44 · sim 0.80

```
Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

VESDA-E VEP-A00-P Guía del producto
38
www.xtralis.com
4.3.5
VESDAnet
VESDAnet es una red de comunicación de datos bidireccional entre los dispositivos de VESDA-E
conectados. La conectividad de VESDAnet está disponible en el detector VEP-A00. Consulte la sección 2.6
para obtener más información.
Es recomendable utilizar cables de par trenzado RS 485 (Belden 9841 - 120 ohmios) para incluir los
dispositivos en la red.
Los cables de red finalizan en los terminales A y B de VESDAnet. El cableado de un dispositivo VESDA-E se
introduce en el detector en un terminal y se conecta a otro dispositivo en VESDAnet desde el otro terminal.
Notas:
l La polaridad de los cables de datos debe mantenerse en toda la red.
l Para que el detector pueda detectar fallos de conexión a tierra en el cableado de VESDAnet, el terminal
de referencia a tierra (Figura 4-33) debe conectarse a una toma a tierra local.
A+
A-
B-
Pantalla
Módulo1
Módulo 2
Módulo 3
Módulo 5
Módulo 4
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
(VESDA-E VEP)
Figura 4-35: Ejemplo de circuito cerrado de la red VESDAnet
El detector VESDA-E VEP-A00 se envía con los terminales A y B en circuito de VESDAnet. Retire las
conexiones A y B antes de conectar el detector a VESDAnet. Si el detector no debe conectarse a la red con
otros dispositivos, no retire las conexiones A y B.
Pantalla
A-
A+
Pantalla
B-
B+
Figura 4-36: Circuito cerrado para detectores independientes con función de VESDAnet
Nota:
Para obtener más información
[… contenido truncado para legibilidad]
```

**[F5]** `VESDA-E VEP` · *Nota: Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E Communications Guide).* · `33977_13_VESDA-E_VEP-A10-P_Product_Guide_A4_Spanish_lores` p.46 · sim 0.80

```
Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

Nota:
Para obtener más información, consulte la guía de comunicaciones de VESDA-E (VESDA-E
Communications Guide).

VESDA-E VEP-A10-P Guía del producto
40
www.xtralis.com
4.3.5
VESDAnet
VESDAnet es una red de comunicación de datos bidireccional entre los dispositivos de VESDA-E
conectados. La conectividad de VESDAnet está disponible en el detector VEP-A10-P. Consulte la sección
2.6 para obtener más información.
Es recomendable utilizar cables de par trenzado RS 485 (Belden 9841 - 120 ohmios) para incluir los
dispositivos en la red.
Los cables de red finalizan en los terminales A y B de VESDAnet. El cableado de un dispositivo VESDA-E se
introduce en el detector en un terminal y se conecta a otro dispositivo en VESDAnet desde el otro terminal.
Notas:
l La polaridad de los cables de datos debe mantenerse en toda la red.
l Para que el detector pueda detectar fallos de conexión a tierra en el cableado de VESDAnet, el terminal
de referencia a tierra (Figura 4-33) debe conectarse a una toma a tierra local.
A+
A-
B-
Pantalla
Módulo1
Módulo 2
Módulo 3
Módulo 5
Módulo 4
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
A+
A-
B-
Pantalla
Pantalla
B+
(VESDA-E VEP)
Figura 4-35: Ejemplo de circuito cerrado de la red VESDAnet
El detector VESDA-E VEP-A10-P se envía con los terminales A y B en circuito de VESDAnet. Retire las
conexiones A y B antes de conectar el detector a VESDAnet. Si el detector no debe conectarse a la red con
otros dispositivos, no retire las conexiones A y B.
Pantalla
A-
A+
Pantalla
B-
B+
Figura 4-36: Circuito cerrado para detectores independientes con función de VESDAnet
Nota:
Para obtener más informa
[… contenido truncado para legibilidad]
```

### Respuesta del bot

```
Para responderte con precisión, ¿qué modelo concreto de VESDA estás instalando?

Los fragmentos que tengo cubren modelos distintos (familia VLF y familia VESDA-E), y el cableado varía entre ellos. Si me indicas el modelo exacto que aparece en la etiqueta del equipo, te doy el procedimiento específico.
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

**Razón del judge:** La pregunta '¿Cómo se cablea la VESDA?' es ambigua porque los fragmentos F1-F5 cubren al menos cinco modelos distintos (VLF-500, VLF-250, VESDA-E VEU, VESDA-E VEP-A00, VESDA-E VEP-A10-P) con procedimientos de cableado diferentes; el bot identifica correctamente esta ambigüedad y pide UN detalle concreto (el modelo exacto) antes de responder, lo que coincide exactamente con la conducta esperada 'ask_clarification'. No hace afirmaciones técnicas inventadas, por lo que corpus_faithful y citation_fa

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general — familias VESDA/VESDA-E de Xtralis`):**

"VESDA" es una familia muy amplia. El bot debería listar candidatos: **VESDA clásica** (VLF-250/VLF-500), **VESDA-E** (VEU, VEP, VES, VEA — A00/A10), y preguntar también si se cablea a VESDAnet o a entrada de central. El bot lo hace bien: enumera VLF y VESDA-E aunque podría haber sido más específico (VEP, VEU, VEA, VES).

**Calidad de los chunks:**

- F3-F5 tienen contenido prácticamente idéntico ("VESDAnet ... Belden 9841 - 120 ohmios... A+ A- B- B+") — **duplicación entre modelos similares** (VEU, VEP-A00, VEP-A10-P). El retrieval mete 3 chunks redundantes.
- F1 y F2 son idénticos en estructura (mismo manual base "VLF-XXX Guía del producto" pero distinto modelo) — patrón aceptable porque son productos diferentes.
- `[TABLA EXTRAÍDA]` en F1/F2 mal aplicada sobre un pie de figura ("A: Bloquedelterminal,conectores1-20").
- Metadata correcta: section_header coincide con contenido.

**Comparación con bot:**

- Pidió clarificación **enumerando familias** (VLF y VESDA-E) — buena práctica.
- Mejor que am001/am006: no se limita a "qué modelo" genérico.
- Mejorable: dentro de VESDA-E podría enumerar sub-modelos (VEU/VEP/VEA/VES).
- No inventó datos.

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Buena respuesta de clarificación con familias enumeradas. Pasa cómodamente.
- **Origen del problema:** chunk-extraction (tabla mal aplicada) + retrieval (duplicación VEU/VEP/VEP-A10) — no afectan a la respuesta.

---

## am008 — judge dice **PASS ✓** · (8/8)

**Pregunta del técnico:** ¿Qué significa el código de error 7?

**Conducta esperada:** `ask_clarification` · **observada:** `ask_clarification`

**Keyword score:** 3/4 hits · missing: `['contexto']` · **keyword_pass:** `False`

> _Notas YAML: Código de error sin contexto — bot debe pedir al menos fabricante. TECH_DEBT #23 attempt revertido sesión 19; cuando se reimplemente via tool use / prompt routing, recalibrar a answer_with_clarify._
> ⚠️ keyword=FAIL ∧ judge=PASS — sospechar judge lenient o keyword frágil

### Fragmentos que el bot usó (top 5)

**[F1]** `ID2000` · *1.1 Mensajes de avería - Causas posibles y soluciones* · `MIDT180` p.59 · sim 0.70

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

**[F2]** `ID2000` · *Apéndice 1* · `MIDT180` p.59 · sim 0.70

```
Apéndice 1

Apéndice 1

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

**[F3]** `ID2000` · *Apéndice 1* · `MIDT180` p.59 · sim 0.70

```
Apéndice 1

Apéndice 1

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

**[F4]** `ID2000` · *Avería central 17 - Tarjeta no encontrada* · `MIDT180` p.59 · sim 0.70

```
Avería central 17 - Tarjeta no encontrada

Avería central 17 - Tarjeta no encontrada

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

**[F5]** `ID2000` · *Avería de sistema - Avería de LIB-CPU Avería del driver LIB Avería central 5 - Reinicio de alimentación Avería de sistem* · `MIDT180` p.59 · sim 0.69

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

### Respuesta del bot

```
¿De qué central o equipo es ese "código de error 7"? Necesito fabricante y modelo para darte la interpretación correcta — el mismo código significa cosas distintas en paneles distintos.
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

**Razón del judge:** La pregunta '¿Qué significa el código de error 7?' es ambigua: no especifica fabricante ni modelo, y los fragmentos disponibles (F1-F5) solo cubren el panel ID2000 de Notifier con códigos de avería nombrados (ej. 'Avería central 17', 'Avería central 5'), sin ninguna entrada para un 'código de error 7' genérico. El bot correctamente pide un detalle concreto (fabricante y modelo) antes de responder, lo cual es la conducta esperada (ask_clarification). No hace afirmaciones técnicas inventadas, es h

### Tu calibración

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL (tacha lo que no corresponda)
- **Dimensión equivocada(s) del judge** (si aplica): _(citation_faithful / corpus_faithful / relevant / helpful / honest / behavior_match)_
- **Nota / por qué:**

**Calibración Claude:**

**Respuesta de referencia (basada en `conocimiento general`):**

"Código de error 7" sin contexto es completamente ambiguo: en un ID2000 sería "Avería central 7" (no documentado en chunks); en CAD-150/250 hay códigos numerados distintos; en Morley Dimension hay otra serie; en FAAST son códigos de evento distintos. El bot debería pedir fabricante + modelo + contexto (¿pantalla LCD?, ¿código parpadeo de LED?, ¿app móvil?). La nota YAML aclara que es categoría `ask_clarification` (TECH_DEBT #23 sobre `answer_with_clarify` aplazado).

**Calidad de los chunks:**

- F1, F2, F3, F4, F5 son **todos del ID2000 página 59** (MIDT180) — **duplicación masiva** (5/5 chunks del mismo panel y página), distintos section_headers fragmentarios ("1.1", "Apéndice 1", "Avería central 17", "Avería de sistema..."). Falla de chunking estrategia: misma página partida en headers arbitrarios.
- El contenido recuperado no menciona ningún "código 7" — solo códigos 5, 17, 29.
- Ningún chunk de otros fabricantes (Detnov, Morley, FAAST) pese a que tienen mensajes de error.

**Comparación con bot:**

- Pidió clarificación pidiendo fabricante y modelo, con observación didáctica útil ("el mismo código significa cosas distintas en paneles distintos") — buena formulación.
- Omisión: no preguntó por el contexto (pantalla LCD vs parpadeo de LED), uno de los keywords esperados.
- No inventó datos pese a que F1-F5 hablan de "Avería central 5/17/29" (podría haber dicho "no tengo código 7 documentado pero sí 5/17/29 para ID2000" — no lo hace, lo cual es defensivo pero conservador).

**Veredicto:**
- [x] **De acuerdo** con el judge / [ ] **En desacuerdo**
- **Dimensión equivocada(s) del judge:** ninguna
- **Nota / por qué:** Conducta correcta. La nota YAML marca recalibración futura a `answer_with_clarify` (proporcionar lo que se sabe + pedir contexto faltante); con la política actual `ask_clarification`, el bot acierta.
- **Origen del problema:** retrieval (5/5 chunks del mismo panel-página, sin diversidad) + chunk-extraction (headers fragmentarios de la misma página) + behavior parcialmente mejorable (no pidió contexto del mensaje).

---

