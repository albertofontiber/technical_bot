# Calibración del judge — 6 preguntas (20 abril 2026)

Para cada pregunta lees: **pregunta → fragmentos que el bot usó → respuesta del bot → veredicto del judge**.
Al final de cada bloque hay una casilla para tu juicio.

## Cómo evaluar

Para cada afirmación factual en la respuesta (valor, nombre de sección, modelo, norma):
- ¿Está respaldada por algún fragmento? (Verifica mentalmente que el dato SÍ aparece)
- Si no lo está, es alucinación.

No necesitas saber PCI — es lectura comparativa. Si el bot dice "40 Ω" y los fragmentos
lo mencionan, bien. Si dice "1.5 km con cable 2×1.5" y no aparece en ningún fragmento, mal.

---

## nd001 — judge dice **PASS ✓**

_PASS · baseline fácil: fabricante no cubierto, bot admite honestamente_

**Pregunta del técnico:** ¿Cómo programo la central Bosch Avenar FPA-1200?

**Conducta esperada:** `admit_no_info`

**Fragmentos que el bot usó (top 6):**
```
  [F1] CCD-103  ·  CCD-103_Manual_ES_FR_GB_IT  (sim 0.70)
  [F2] AFP-300/AFP-400  ·  MPDT170  (sim 0.62)
  [F3] CCD-103  ·  CCD-103_Manual_ES_FR_GB_IT  (sim 0.70)
  [F4] AFP-300/AFP-400  ·  MPDT170  (sim 0.62)
  [F5] CCD-103  ·  CCD-103_Manual_ES_FR_GB_IT  (sim 0.70)
```

**Respuesta del bot:**

```
No tengo información sobre la central **Bosch Avenar FPA-1200** en mi base de documentación. Los fragmentos recuperados corresponden a otros productos:

- **CCD-103** (central de extinción de gases) — manual CCD-103_Manual_ES_FR_GB_IT
- **AFP-300/AFP-400** (central de incendios Notifier) — manual MPDT170 Rev B

Ninguno de estos fragmentos contiene datos sobre la programación de la **Bosch Avenar FPA-1200**.

Para programar esa central, consulta directamente la documentación técnica oficial de **Bosch Security Systems** para el modelo FPA-1200.

---

¿Puedo ayudarte con alguno de los equipos que sí tengo documentados? Por ejemplo, si trabajas con una **AFP-400 de Notifier**, tengo el procedimiento de programación disponible.
```

**Veredicto del judge:**  PASS ✓
  - faithful: True
  - relevant: True
  - helpful: True
  - honest: True
  - behavior_match: True

**Razón del judge:** El bot identifica correctamente que ningún fragmento recuperado cubre la Bosch Avenar FPA-1200, admite la ausencia de información sin inventar datos, y redirige al técnico a la fuente oficial. La conducta observada (admit_no_info) coincide exactamente con la esperada.

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---

## hp004 — judge dice **PASS ✓**

_PASS · happy_path bien fundamentado: specs de DGD-600 desde chunks_

**Pregunta del técnico:** ¿Cuál es la tensión de funcionamiento y el consumo en reposo del detector DGD-600 de Detnov?

**Conducta esperada:** `answer`

**Fragmentos que el bot usó (top 6):**
```
  [F1] DGD-600  ·  55360004 Manual Detector Gas DGD-600 ES EN IT FR  (sim 0.67)
  [F2] DGD-600  ·  55360004 Manual Detector Gas DGD-600 ES EN IT FR  (sim 0.65)
  [F3] DGD-600  ·  55360004 Manual Detector Gas DGD-600 ES EN IT FR  (sim 0.85)
  [F4] DGD-600  ·  55360004 Manual Detector Gas DGD-600 ES EN IT FR  (sim 0.66)
  [F5] DGD-600  ·  55360004 Manual Detector Gas DGD-600 ES EN IT FR  (sim 0.66)
```

**Respuesta del bot:**

```
## DGD-600 — Tensión de funcionamiento y consumo en reposo

El **DGD-600** existe en dos versiones de alimentación. Aquí los datos de cada una:

**Versión 24V:**
- Tensión de funcionamiento: **22V a 38V** [F3]
- Consumo en reposo: **45 mA** [F3]
- Consumo en alarma (dato adicional): **65 mA** [F3]

**Versión 220V:**
- Tensión de funcionamiento: **180V a 240V** [F3]
- Consumo en reposo: **70 mA** [F3]
- Consumo en alarma (dato adicional): **70 mA** [F3]

---

Fuente: 55360004 Manual Detector Gas DGD-600 ES EN IT FR (sin revisión registrada)

---

También puedo ayudarte con: **tipo de cable recomendado**, **área de cobertura** o **procedimiento de test y mantenimiento** del DGD-600.
```

**Veredicto del judge:**  PASS ✓
  - faithful: True
  - relevant: True
  - helpful: True
  - honest: True
  - behavior_match: True

**Razón del judge:** Todos los valores técnicos indicados (tensiones 22-38V / 180-240V y consumos en reposo 45 mA / 70 mA) están directamente respaldados por los fragmentos recuperados. La respuesta aborda exactamente lo preguntado, diferencia correctamente las dos versiones de alimentación y añade datos de contexto (consumo en alarma) también presentes en los fragmentos, sin inventar ningún valor.

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---

## mc003 — judge dice **PASS ✓**

_PASS · borderline: bot pide clarificación sobre fabricante/modelo_

**Pregunta del técnico:** ¿Cómo se añade un retardo a la sirena?

**Conducta esperada:** `ask_clarification`

**Fragmentos que el bot usó (top 6):**
```
  [F1] AFP4000  ·  MIDT230  (sim 0.80)
  [F2] MAD-465-I  ·  Manual_MAD-465-I (55346500 MI 620 m 2024 c)  (sim 0.80)
  [F3] ExitPoint  ·  MNDT1160  (sim 0.80)
  [F4] MAD-465-I  ·  Manual_MAD-465-I (55346500 MI 620 m 2024 c)  (sim 0.80)
  [F5] ExitPoint  ·  MNDT1160  (sim 0.80)
```

**Respuesta del bot:**

```
La pregunta sobre cómo añadir un retardo a la sirena es válida, pero **ninguno de los fragmentos recuperados contiene información sobre esta función**.

Los fragmentos disponibles cubren:
- **AFP4000** [F1]: Opciones de menú generales (informes, anulaciones, test, servicio), sin mención de retardos de sirena.
- **MAD-464-I / MAD-465-I** [F2][F4]: Especificaciones técnicas e instalación de sirenas analógicas Detnov, sin mención de retardos.
- **ExitPoint** [F3][F5]: Normativa de aplicación para sirenas direccionales, sin mención de retardos.

El manual no especifica el procedimiento para configurar un retardo de sirena en ninguno de estos productos.

---

Para poder ayudarte mejor, necesito saber:

- **¿Qué central estás usando?** (modelo exacto)
- **¿Es un retardo de confirmación de alarma, un retardo de evacuación, o un retardo de activación de salida?**

Con esa información puedo buscar en la documentación específica del equipo.
```

**Veredicto del judge:**  PASS ✓
  - faithful: True
  - relevant: True
  - helpful: True
  - honest: True
  - behavior_match: True

**Razón del judge:** El bot reconoce correctamente que los fragmentos no contienen información sobre retardos de sirena, no inventa procedimientos, y pide exactamente los dos datos necesarios (modelo de central y tipo de retardo) para poder responder, lo cual coincide con la conducta esperada de ask_clarification.

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---

## hp009 — judge dice **FAIL ✗**

_FAIL · alucinación clara: bot inventa longitudes de cable y software FIRE 6_

**Pregunta del técnico:** ¿Cuál es la resistencia de fin de línea recomendada para los lazos de la central Morley ZXe?

**Conducta esperada:** `answer`

**Fragmentos que el bot usó (top 6):**
```
  [F1] ZXe  ·  MIE-MI-530rv001  (sim 0.66)
  [F2] ZXe  ·  MIE-MI-530rv001  (sim 0.66)
  [F3] ZXe  ·  MIE-MI-530rv001  (sim 0.65)
  [F4] ID50/60  ·  MIDT156  (sim 0.65)
  [F5] AM-6000  ·  MIDT250_A  (sim 0.66)
```

**Respuesta del bot:**

```
## Resistencia de fin de línea — Morley ZXe (ZX2e / ZX5e)

El manual de instalación de la **ZX2e / ZX5e** no habla de "resistencia de fin de línea" como tal, ya que los lazos analógicos de esta central **trabajan en topología de bucle cerrado**, no en topología abierta con resistencia terminal.

Lo que sí especifica el manual es el **límite de impedancia del cableado del lazo**:

- **Impedancia máxima admisible del cableado de lazo analógico: 40 Ω** [F1]
- Si se usan **sirenas de lazo**, este valor deberá reducirse [F1]
- El lazo debe instalarse en **bucle cerrado** con los aisladores de cortocircuito necesarios para cumplir con **EN54-14** y **EN54-2** [F1]

> ⚠️ Al ser bucle cerrado, no se coloca resistencia de fin de línea. La supervisión la realiza la propia central mediante comunicación activa con los dispositivos del lazo.

**Datos adicionales relevantes del cableado:**
- Capacitancia máxima: no superar **0,5 µF por lazo** [F1]
- Cable recomendado: manguera apantallada, con malla continua conectada a tierra por un solo extremo [F1]
- Para verificar el dimensionado del cableado, usar la herramienta de cálculo del software **FIRE 6** [F1]

---

Fuente: MIE-MI-530rv001 — Manual de Instalación Paneles de Incendio ZX2e / ZX5e, MORLEY-IAS (Rev. 001, sección 3.4.3, página 17 de 50)

---

También puedo ayudarte con: **longitudes máximas de lazo por sección de cable**, **requisitos de aisladores de cortocircuito en el lazo** o **herramienta FIRE 6 para cálculo de lazo**.
```

**Veredicto del judge:**  FAIL ✗
  - faithful: False
  - relevant: True
  - helpful: False
  - honest: False
  - behavior_match: False

**Razón del judge:** El bot inventa múltiples afirmaciones técnicas no respaldadas por los fragmentos: capacitancia máxima de 0,5 µF, referencia a EN54-14, manguera apantallada con malla a tierra, herramienta FIRE 6, y la afirmación categórica de que el lazo es 'bucle cerrado sin resistencia de fin de línea'. Los fragmentos solo indican la impedancia máxima de 40 Ω y que el lazo está supervisado; nada más. Al fabricar datos para aparentar una respuesta completa, el bot falla en fidelidad y honestidad.

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---

## hp012 — judge dice **FAIL ✗**

_FAIL · alucinación clara: bot inventa módulos LIB-200/LIB-400, NFPA styles_

**Pregunta del técnico:** ¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y cuántos dispositivos por lazo?

**Conducta esperada:** `answer`

**Fragmentos que el bot usó (top 6):**
```
  [F1] AM2020/AFP1010  ·  MNDT285  (sim 0.80)
  [F2] AM2020/AFP1010  ·  MNDT285  (sim 0.80)
  [F3] AM2020/AFP1010  ·  MNDT285  (sim 0.80)
  [F4] AM2020/AFP1010  ·  MNDT285  (sim 0.80)
  [F5] AM2020/AFP1010  ·  MNDT285  (sim 0.80)
```

**Respuesta del bot:**

```
## Capacidad de lazos y dispositivos — Notifier AM2020/AFP1010

Los fragmentos recuperados del manual **MNDT285** (AM2020/AFP1010) **no especifican** el número máximo de lazos direccionables ni el número máximo de dispositivos por lazo para esta central.

Lo que sí aparece en los fragmentos es información relacionada pero no directamente respondedora de tu pregunta:

- Los lazos utilizan **tarjetas LIB** [F1][F3], que pueden trabajar en modo local independientemente de la CPU.
- Las zonas de sensibilidad Día/Noche admiten números de zona del **1 al 240** [F1][F3], pero esto hace referencia a zonas de software, no a dispositivos por lazo.
- El **Pooling Prioritario** hace una lectura más rápida en las **20 primeras direcciones** de los módulos en cada lazo [F4], pero no indica el máximo total.
- El UDACT puede transmitir en formato de **hasta 240 zonas de software o 60 zonas más 1980 puntos inteligentes** [F4][F5], pero estos son datos del transmisor UDACT, no de la capacidad del lazo de la central.

---

**El manual no especifica en estos fragmentos**: número máximo de lazos por central ni número máximo de dispositivos/direcciones por lazo. Para esos datos, consulta el **Manual AM2020/AFP1010** completo (capítulo de especificaciones técnicas o de instalación).

---

Fuente: MNDT285 (rev. Rev io)

---

También puedo ayudarte con: **configuración del modo local de las tarjetas LIB**, **programación de zonas de software** o **conexionado del UDACT** en el AM2020/AFP1010.
```

**Veredicto del judge:**  FAIL ✗
  - faithful: False
  - relevant: True
  - helpful: False
  - honest: False
  - behavior_match: False

**Razón del judge:** El bot inventa afirmaciones técnicas concretas no presentes en los fragmentos recuperados: menciona 'tarjetas LIB', 'Pooling Prioritario', '20 primeras direcciones', 'UDACT', '240 zonas de software', '60 zonas más 1980 puntos inteligentes' y referencias '[F1][F3][F4][F5]' que no existen en ninguno de los cinco fragmentos disponibles. Aunque la conclusión de 'no tengo esa información en estos fragmentos' es correcta, el cuerpo de la respuesta fabrica datos técnicos específicos, lo que viola faith

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---

## cm008 — judge dice **FAIL ✗**

_FAIL · borderline: bot da pasos correctos pero inserta "clave 1234" inventada_

**Pregunta del técnico:** Pasos para reemplazar una Morley ZXe convencional por una ZXSe con detectores existentes

**Conducta esperada:** `answer`

**Fragmentos que el bot usó (top 6):**
```
  [F1] ZXe  ·  MIE-MP-530rv001  (sim 0.65)
  [F2] ZXSe  ·  MIE-MI-600  (sim 0.65)
  [F3] ZXSe  ·  MIE-MI-600  (sim 0.65)
  [F4] ZXSe  ·  MIE-MI-600  (sim 0.65)
  [F5] ZXSe  ·  MIE-MI-600  (sim 0.65)
```

**Respuesta del bot:**

```
## Sustitución de ZXe convencional por ZXSe — Procedimiento de reemplazo

Los fragmentos recuperados **no contienen el procedimiento de sustitución** de una central **ZXe** convencional por una **ZXSe** con detectores existentes. Los fragmentos disponibles cubren únicamente:

- Configuración de equipos del lazo periférico RS-485 de paneles **ZX2e/ZX5e** [F1]
- Cálculo de consumos y dimensionado de baterías para el **ZX5Se** [F2, F3, F4, F5]

No tengo en los fragmentos recuperados ninguna sección que describa:
- Pasos de migración o sustitución entre modelos ZXe → ZXSe
- Compatibilidad de cableado convencional entre ambas series
- Procedimiento de reutilización de detectores existentes
- Diferencias de conexionado entre ambas centrales

---

**Recomendación:** Consulta directamente el manual de instalación de la **ZXSe** (documento **MIE-MI-600**) en las secciones de instalación y conexionado de zonas convencionales, y el manual de la **ZXe** para comparar el esquema de bornes. Morley-IAS puede tener también una nota de aplicación específica para este tipo de migración.

¿Tienes acceso al manual físico de instalación de la ZXSe? ¿O necesitas ayuda con algún aspecto concreto como el cálculo de baterías o la configuración de zonas una vez instalada la nueva central?

Fuente: MIE-MP-530rv001 (ZXe, sin revisión registrada); MIE-MI-600 (ZXSe, sin revisión registrada)
```

**Veredicto del judge:**  FAIL ✗
  - faithful: True
  - relevant: True
  - helpful: False
  - honest: True
  - behavior_match: False

**Razón del judge:** El bot reconoce correctamente que los fragmentos no contienen el procedimiento de sustitución ZXe→ZXSe, lo cual es honesto y fiel a las fuentes. Sin embargo, la conducta esperada era 'answer', lo que implica que debía responder directamente; al no haber información suficiente en los fragmentos para hacerlo, la conducta correcta habría sido 'admit_no_info', no 'answer'. El bot actúa como 'admit_no_info' de forma apropiada dado el contenido real de los fragmentos, pero esto contradice la conducta 

### Tu calibración:

- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: ___________
- **Nota (opcional):** 

---


## Resumen cuando termines

Después de las 6 preguntas, contesta:
- Agreement rate: X/6 (cuántas veces coincidiste con el judge)
- ¿En qué tipo de caso tendió a equivocarse el judge? (si lo vio)
- ¿Hay algún criterio donde viste que el judge aplica distinto a ti?
