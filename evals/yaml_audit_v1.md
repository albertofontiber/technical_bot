# Audit del YAML — `expected_behavior` de las 52 preguntas

Base: último eval con judge corregido (`logs/eval_20260421T192338Z.json`) — 54% judge PASS.

## Cómo usar este documento

Para cada pregunta lees:
- **pregunta**
- **expected_behavior actual** del YAML
- **observed_behavior** del bot en el último run
- **judge verdict** (PASS / FAIL)
- **resumen del contenido disponible en los chunks** (para que juzgues si había info suficiente)

Marcas una de:
- ✅ **correcto** — el `expected_behavior` actual está bien
- 🔄 **debería ser X** — indica qué (answer / ask_clarification / admit_no_info)
- ❓ **dudoso** — no lo sé, discutirlo

Reglas rápidas para calibrar:
- `answer` → el corpus SÍ tiene info suficiente; el bot debería responder
- `ask_clarification` → pregunta es ambigua (faltan datos del técnico); bot debería pedir detalles
- `admit_no_info` → corpus NO cubre ese producto/fabricante; bot debería decir "no tengo"

El criterio CLAVE: ¿los chunks que el retriever trajo en el último run son suficientes para responder?

- Si sí y es directa → `answer`
- Si sí pero la pregunta tiene ambigüedad (modelo X o Y?) → `ask_clarification`
- Si no, y es porque el producto no está en el corpus → `admit_no_info`

---


## Categoría: `happy_path` (20 preguntas)

### hp001  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Detnov CAD-250, ¿cómo se entra al menú de programación avanzada?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: CAD-250 (sim 0.80), CAD-250 (sim 0.80), CAD-250 (sim 0.80), CAD-250 (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que los fragmentos disponibles no contienen información sobre el acceso al menú de programación avanzada, admite la limitación sin inventar datos, y orienta al técnico hacia el manual de usuario/programación. La conducta esperada era 'answer', pero d..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp002  —  actualmente `expected_behavior: answer`

**Pregunta:** El detector ASD535 de Detnov está dando una alarma intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: ASD535 (sim 0.65), MINILÁSER25 (sim 0.65), ASD535 (sim 0.80), ASD535 (sim 0.65)
- Rationale judge: _El bot responde directamente con información accionable, citando correctamente los fragmentos disponibles. Crucialmente, es honesto al advertir explícitamente que el procedimiento de diagnóstico detallado proviene del manual del MINILÁSER 25 (F2) y no del manual específico del AS..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp003  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo se conectan las baterías de 24V en la Detnov CAD-150?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: CAD-150-8 (sim 0.65), CAD-150-8 (sim 0.65), CAD-150-8 (sim 0.65), CAD-150-8 (sim 0.65)
- Rationale judge: _El bot cita datos técnicos concretos ([F4]) como capacidades de batería (7 A/h, 18 A/h, 24 A/h) y un procedimiento de conexionado con advertencia textual, pero NINGUNO de esos datos aparece en los fragmentos recuperados (que solo contienen índices y descripciones del panel de con..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp004  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cuál es la tensión de funcionamiento y el consumo en reposo del detector DGD-600 de Detnov?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: DGD-600 (sim 0.67), DGD-600 (sim 0.65), DGD-600 (sim 0.85), DGD-600 (sim 0.66)
- Rationale judge: _Todas las afirmaciones técnicas (tensiones de funcionamiento y consumos en reposo para ambas versiones) están correctamente respaldadas por los fragmentos disponibles, especialmente el Fragmento 3. El dato adicional sobre consumo en alarma también aparece en los fragmentos y se p..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp005  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Notifier ID3000, ¿cómo se programa una zona para que active una salida de sirena solo cuando haya coincidencia de dos detectores?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que los fragmentos disponibles solo cubren ajuste de fecha y hora y no contienen información sobre programación de zonas ni lógica de doble detector. Al no tener información suficiente, admite la limitación con honestidad, orienta al técnico hacia el..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp006  —  actualmente `expected_behavior: answer`

**Pregunta:** La Notifier AFP-400 muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: AFP-300/AFP-400 (sim 0.80), AFP-300/AFP-400 (sim 0.80), AFP-300/AFP-400 (sim 0.80), AFP-300/AFP-400 (sim 0.80)
- Rationale judge: _El bot es honesto al reconocer que los fragmentos no contienen información sobre el aviso 'Tierra', y sus afirmaciones sobre el contenido de los fragmentos son fieles. Sin embargo, la conducta esperada es 'answer' (responder directamente), lo que implica que había información suf..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp007  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo se realiza el test anual de un detector VESDA-E VEP según el manual del fabricante?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: VESDA-E VEP (sim 0.73), VESDA-E VEP (sim 0.73), VESDA-E VEP (sim 0.73), VESDA-E VEP (sim 0.73)
- Rationale judge: _La respuesta es mayormente fiel a los fragmentos, pero incluye afirmaciones sobre el modo en espera que van más allá de lo disponible en los fragmentos recuperados: concretamente, que 'detiene la detección de alarmas pero NO la detección ni señalización de fallos', que 'se señali..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp008  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Qué detectores de humo analógicos son compatibles con la Notifier ID3000?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80)
- Rationale judge: _El bot responde directamente con los detectores de humo analógicos listados en el Fragmento 1, los identifica correctamente por modelo y descripción, y excluye apropiadamente los térmicos con una explicación clara. Todas las afirmaciones están soportadas por los fragmentos dispon..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp009  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cuál es la resistencia de fin de línea recomendada para los lazos de la central Morley ZXe?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: ZXe (sim 0.66), ZXe (sim 0.80), ZXe (sim 0.80), ZXe (sim 0.80)
- Rationale judge: _El bot inventa dos afirmaciones no respaldadas por ningún fragmento: la capacitancia máxima de 0,5 µF y la referencia a EN54-14 con aisladores de cortocircuito en bucle cerrado. Ninguno de estos datos aparece en los fragmentos recuperados, lo que hace la respuesta infiel y deshon..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp010  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Morley DXc, ¿cómo se añade un nuevo detector al lazo tras la puesta en marcha inicial?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: DXc (sim 0.65), DXc (sim 0.65), DXc (sim 0.64), DXc (sim 0.64)
- Rationale judge: _El bot responde directamente con la información disponible en los fragmentos (cableado físico, polaridad, impedancia, longitud máxima, aisladores), todas las afirmaciones técnicas concretas están soportadas por los fragmentos recuperados, y admite honestamente que el procedimient..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp011  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: RP1r (sim 0.58), RP1r (sim 0.65), RP1r (sim 0.65), RP1r (sim 0.65)
- Rationale judge: _El bot inventa afirmaciones no soportadas por los fragmentos: menciona 'UNE-EN 12094-1:2004, apartado 4.27' y el pulsador ABORT como causa de bloqueo del rearme, pero ningún fragmento contiene esa referencia normativa ni asocia el ABORT con el problema descrito. Además, los fragm..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp012  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y cuántos dispositivos por lazo?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: AM2020/AFP1010 (sim 0.80), AM2020/AFP1010 (sim 0.80), AM2020/AFP1010 (sim 0.80), AM2020/AFP1010 (sim 0.80)
- Rationale judge: _Todas las afirmaciones técnicas están respaldadas por los fragmentos: 198 dispositivos por lazo y 1.980 puntos totales aparecen explícitamente en F1. El bot deduce correctamente 10 lazos mediante aritmética directa de dos datos del manual, y es transparente al señalar que es una ..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp013  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo se cambia la batería tampón de la Detnov ADW535 sin perder configuración?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: ADW535 (sim 0.65), ADW535 (sim 0.65), ADW535 (sim 0.65), ADW535 (sim 0.65)
- Rationale judge: _El bot admite correctamente que los fragmentos recuperados no contienen información sobre el cambio de batería tampón, lo cual es exacto. Además, añade valor señalando que el capítulo 10.1 del manual (mencionado en el historial de revisiones de F2) trata sobre 'Procedimiento con ..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp014  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo se conecta un módulo de aislamiento de línea en un lazo ID2000?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: ID2000 (sim 0.70), ID2000 (sim 0.69), ID-200 (sim 0.69), ID-200 (sim 0.69)
- Rationale judge: _El bot responde directamente con la información disponible en los fragmentos ID2000 (límites EN54-2, procedimiento previo, posicionamiento en el lazo), reconoce honestamente que los fragmentos no incluyen el conexionado terminal a terminal del módulo aislador, y distingue correct..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp015  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Detnov CCD-103, ¿cómo se desactiva un detector individualmente sin afectar al resto del lazo?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: CCD-103 (sim 0.65), CCD-103 (sim 0.65), CCD-103 (sim 0.65), CCD-103 (sim 0.65)
- Rationale judge: _El bot responde directamente (conducta 'answer') reconociendo que los fragmentos no contienen el procedimiento solicitado, pero aporta contexto técnico válido y soportado (la CCD-103 es una central convencional de 3 zonas [F5]) para explicar por qué la desactivación individual no..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp016  —  actualmente `expected_behavior: answer`

**Pregunta:** Un detector B501RF de Notifier no responde tras sustituir la batería. ¿Qué procedimiento seguir?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: B501RF (sim 0.80), B501RF (sim 0.80), B501RF (sim 0.80), B501RF (sim 0.80)
- Rationale judge: _El bot inventa información significativa no presente en los fragmentos: los estados LED detallados (pulsación verde larga, 3 luces verdes intermitentes, luz roja/verde doble cada 14 s, luz verde/ámbar cada 14 s, luz ámbar cada 1 s) no aparecen en ninguno de los fragmentos recuper..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp017  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo se programa el retardo de salida de alarma principal en la Notifier PEARL?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: PEARL (sim 0.80), PEARL (sim 0.65), PEARL (sim 0.80), PEARL (sim 0.80)
- Rationale judge: _El bot inventa una sección '5.1.4 Retardos de activación de salidas' que no aparece en ninguno de los fragmentos recuperados (el índice visible en F3/F4/F5 solo llega hasta la sección 5 sin detallar subsecciones), lo que rompe faithful. Además, la conducta esperada era 'answer' p..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp018  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cuál es el conexionado correcto de una sirena convencional en la Morley ZXe zona 1?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: ZXe (sim 0.71), ZXe (sim 0.71), ZXe (sim 0.82), ZXe (sim 0.82)
- Rationale judge: _Todas las afirmaciones técnicas (terminales A±/B±/C±/D±, bloques TB6-TB10, RFL 6,8KΩ 0,5W, diodo integrado, polarización inversa en reposo, límite de 1A, referencia a sección 3.4.13) están respaldadas por los Fragmentos 1 y 2. El bot aclara honestamente que la pregunta menciona '..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp019  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cuál es el rango de temperatura de funcionamiento de los detectores Detnov serie ASD?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: unknown (sim 0.80), ECO1005 (sim 0.80), NFXI-VIEW (sim 0.80), S3-T1 (sim 0.80)
- Rationale judge: _Los fragmentos recuperados no contienen ninguna información sobre detectores Detnov serie ASD, por lo que el bot actuó correctamente admitiendo la ausencia de información y redirigiendo al técnico a fuentes apropiadas. La conducta observada (admit_no_info) coincide con la esperad..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### hp020  —  actualmente `expected_behavior: answer`

**Pregunta:** En la Notifier INSPIRE, ¿cómo se configuran las contraseñas de nivel 2 y nivel 3?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: INSPIRE (sim 0.80), INSPIRE (sim 0.80), INSPIRE (sim 0.80), INSPIRE (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que ninguno de los fragmentos recuperados contiene información sobre configuración de contraseñas de nivel 2 y nivel 3, sin inventar datos. Admite la limitación con honestidad, orienta al técnico hacia los manuales correctos (especialmente HOP-138-8E..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---


## Categoría: `ambiguous_model` (8 preguntas)

### am001  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cómo programo el sistema 5000?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: Systema 5000 (sim 0.72), Systema 5000 (sim 0.68), Systema 5000 (sim 0.69), Systema 5000 (sim 0.69)
- Rationale judge: _El bot inventa la clave de acceso '231 3112' y describe LEDs de 'CONTRASEÑA ACEPTADA' y 'PROGRAM/SERVICIO' que no aparecen en ningún fragmento disponible (el Fragmento 4 está truncado y no revela la clave real); además, la conducta esperada era pedir clarificación ante una pregun..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am002  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** Mi central da error genérico al arrancar, ¿qué hago?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: CCD-100 (sim 0.85), unknown (sim 0.85), unknown (sim 0.85), unknown (sim 0.85)
- Rationale judge: _El bot responde con información técnica fiel al Fragmento 1 (CCD-100) y es útil y honesto, pero la conducta esperada era 'ask_clarification' pura: ante una pregunta ambigua ('error genérico', modelo desconocido), el bot debía pedir UN detalle concreto ANTES de responder, no dar u..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am003  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cuál es el consumo del ASD?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: ASD531 (sim 0.56), ASD531 (sim 0.57), ASD531 (sim 0.55), ASD531 (sim 0.55)
- Rationale judge: _El bot respondió directamente con datos correctos y verificables del Fragmento 1 (75 mA en reposo/fallo, 80 mA en alarma, rango 14-30 VDC), pero la conducta esperada era 'ask_clarification' porque la pregunta '¿Cuál es el consumo del ASD?' es ambigua: podría referirse a distintos..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am004  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿La FAAST es compatible con mi central?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: FAAST XM (sim 0.65), FAAST XM (sim 0.65), FAAST XM (sim 0.65), FAAST XM (sim 0.65)
- Rationale judge: _El bot proporciona información técnica correcta y bien citada sobre los relés y especificaciones eléctricas de la FAAST XM, y al final sí pide la aclaración necesaria (modelo de central). Sin embargo, la conducta esperada era 'ask_clarification' como acción principal: el bot debí..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am005  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cómo reseteo el panel?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: CCD-100 (sim 0.80), CCD-100 (sim 0.80), RP1r (sim 0.80), AM8200 (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que la pregunta es ambigua (no especifica modelo ni tipo de reset), explica honestamente qué información sí está disponible en los fragmentos (efecto del reset en CCD-100, reset automático en AM8200) sin inventar procedimientos que no aparecen, y sol..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am006  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** Necesito añadir un detector al lazo 2 de la ID

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: CAD-250 (sim 0.80), CAD-250 (sim 0.80), ECO1005 (sim 0.80), ECO1005 (sim 0.80)
- Rationale judge: _La conducta esperada era 'ask_clarification' porque 'la ID' es ambigua (no se sabe qué central es), pero el bot asumió que era el CAD-250 y procedió a dar una respuesta técnica extensa. Además, varias afirmaciones técnicas concretas no están soportadas por los fragmentos: la regl..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am007  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cómo se cablea la VESDA?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: VESDA VLI Installation (sim 0.80), ASD532 (sim 0.80), ASD532 (sim 0.80), ASD532 (sim 0.80)
- Rationale judge: _El bot inventa numerosas afirmaciones no respaldadas por los fragmentos: secciones de cable (0,2–2,5 mm²), terminales F-14 a F-18, el procedimiento de conexión paso a paso, las advertencias sobre tarjetas de interfaz y la referencia al documento 18500. El Fragmento 1 solo lista t..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### am008  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Qué significa el código de error 7?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: CCD-103 (sim 0.40), CCD-103 (sim 0.39), CCD-103 (sim 0.39), CCD-103 (sim 0.38)
- Rationale judge: _El bot responde correctamente con información fiel al Fragmento 1 (código 7 = Fallo de sistema, indicador amarillo fijo, sistema no operativo), pero la conducta esperada era 'ask_clarification' porque la pregunta es ambigua (no especifica modelo/fabricante). Sin embargo, los frag..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---


## Categoría: `missing_context` (8 preguntas)

### mc001  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** Tengo una alarma de batería baja que no se quita aunque las baterías son nuevas

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: PS Series (sim 0.80), unknown (sim 0.50), unknown (sim 0.44), unknown (sim 0.48)
- Rationale judge: _El bot identifica correctamente que la pregunta es ambigua (dos productos distintos en los fragmentos) y pide un detalle concreto —el modelo del equipo— antes de responder en profundidad, cumpliendo la conducta esperada 'ask_clarification'. Mientras tanto, ofrece información técn..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc002  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cada cuánto hay que hacer mantenimiento?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: DXc (sim 0.60), DXc (sim 0.59), ASD531 (sim 0.64), ASD531 (sim 0.58)
- Rationale judge: _El bot responde directamente con información de múltiples productos en lugar de pedir clarificación sobre cuál es el producto del técnico, lo que no coincide con la conducta esperada (ask_clarification). Además, incluye afirmaciones sobre las tareas anuales del DXc (p.ej. 'prueba..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc003  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cómo se añade un retardo a la sirena?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: AFP4000 (sim 0.80), MAD-465-I (sim 0.80), ExitPoint (sim 0.80), MAD-465-I (sim 0.80)
- Rationale judge: _La pregunta es ambigua (no especifica producto ni tipo de retardo), y el bot correctamente reconoce que los fragmentos disponibles no contienen información sobre configuración de retardos de sirena, lo admite con honestidad y pide exactamente los detalles necesarios (modelo de ce..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc004  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Dónde se conecta el cable de tierra?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: ID3000 (sim 0.66), ID50 (sim 0.60), FSL100 (sim 0.62), EFS/EM 8 (sim 0.66)
- Rationale judge: _El bot respondió directamente con información técnica de múltiples productos en lugar de pedir clarificación sobre qué modelo está trabajando el técnico, que es la conducta esperada ante una pregunta ambigua. Aunque toda la información técnica está correctamente soportada por los..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc005  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Mi detector antiguo vale para la nueva central?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: DXc (sim 0.57), ID3000 (sim 0.80), TBUD-150 (sim 0.80), ID3000 (sim 0.80)
- Rationale judge: _El bot inventa una afirmación atribuida a [F3] (TBUD-150) sobre 'soporte de no polaridad', dato que no aparece en ningún fragmento disponible, lo que rompe faithful. Además, en lugar de pedir clarificación de forma directa (conducta esperada: ask_clarification), el bot mezcla inf..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc006  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cuál es la distancia máxima de cableado?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: LaserStar (sim 0.66), ZXSe (sim 0.66), ID3000 (sim 0.66), ID2net (sim 0.66)
- Rationale judge: _El bot volcó correctamente todos los datos técnicos de los fragmentos sin inventar nada, pero la conducta esperada era 'ask_clarification': ante una pregunta ambigua que abarca múltiples productos y tipos de cableado, debía pedir UN detalle concreto antes de responder. En cambio,..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc007  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** El sistema me da fault

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: unknown (sim 0.51), unknown (sim 0.51), unknown (sim 0.52), unknown (sim 0.52)
- Rationale judge: _El bot inventa afirmaciones no respaldadas por los fragmentos disponibles: cita 'Alimentación principal — fallo en suministro de red o fusible roto [F1]' y 'Apertura de tapa — mensaje Open cover detected (Serie ONE) [F4]', datos que no aparecen en ninguno de los fragmentos recupe..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### mc008  —  actualmente `expected_behavior: ask_clarification`

**Pregunta:** ¿Cómo pongo la instalación en servicio?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: CAD-150-8 (sim 0.52), AgileIQ (sim 0.50), AgileIQ (sim 0.50), AgileIQ (sim 0.50)
- Rationale judge: _El bot responde con información técnica fiel a los fragmentos disponibles (CAD-150-8 y AgileIQ) y resulta útil, pero la conducta esperada era 'ask_clarification': ante una pregunta ambigua sin especificar producto, el bot debía pedir UN detalle concreto antes de responder. En cam..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---


## Categoría: `not_in_db` (8 preguntas)

### nd001  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cómo programo la central Bosch Avenar FPA-1200?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: ID50 (sim 0.70), TG-Honeywell (sim 0.70), PGD-200 (sim 0.52), PEARL (sim 0.70)
- Rationale judge: _El bot reconoce correctamente que ninguno de los fragmentos recuperados cubre la central Bosch Avenar FPA-1200 y admite la falta de información sin inventar procedimientos. La conducta observada (admit_no_info) coincide exactamente con la esperada, y las referencias a los product..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd002  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** Mi Esser IQ8Quad da error 14

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: ASD532 (sim 0.47), ASD532 (sim 0.47), ASD532 (sim 0.48), ASD532 (sim 0.47)
- Rationale judge: _El bot identifica correctamente que los fragmentos disponibles corresponden al ASD532 y no al Esser IQ8Quad, admite sin inventar que no tiene documentación para ese producto, y dirige al técnico a la fuente correcta. La conducta observada coincide exactamente con 'admit_no_info'...._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd003  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿El detector Apollo XP95 es compatible con la ID3000?

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80)
- Rationale judge: _El bot responde correctamente que el XP95 de Apollo no aparece en la lista de compatibles de la ID3000, y todas las afirmaciones técnicas están soportadas por el Fragmento 1. Sin embargo, la conducta esperada era 'admit_no_info' (el fabricante/producto Apollo XP95 no está cubiert..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd004  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cuál es el consumo de la Aritech ATS 3500?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: ASD535 (sim 0.45), Sistema 5000 (sim 0.45), ASD535 (sim 0.45), Sistema 5000 (sim 0.45)
- Rationale judge: _El bot reconoce correctamente que ninguno de los fragmentos disponibles contiene información sobre la Aritech ATS 3500, identifica con precisión los productos que sí están cubiertos (ASD535 y Sistema 5000), y remite al técnico a la documentación oficial del fabricante. La conduct..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd005  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cómo configuro la UTC FP1200 para tener dos lazos independientes?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: ID3000 (sim 0.70), ZXe (sim 0.70), ID3000 (sim 0.70), ZXe (sim 0.70)
- Rationale judge: _El bot identifica correctamente que ningún fragmento cubre la UTC FP1200, admite la ausencia de información sin inventar procedimientos, y ofrece una recomendación práctica junto con una oferta de ayuda para productos sí documentados. La conducta observada coincide exactamente co..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd006  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cómo se cablea una cámara IP Hikvision DS-2CD2143G0?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: PEARL (sim 0.51), CCD-100 (sim 0.49), PEARL (sim 0.51), PEARL (sim 0.50)
- Rationale judge: _El bot reconoce correctamente que ninguno de los fragmentos disponibles contiene información sobre la cámara IP Hikvision DS-2CD2143G0, admite la ausencia de información sin inventar datos, y redirige al técnico a la fuente correcta. La conducta observada (admit_no_info) coincide..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd007  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cómo mantengo un grupo de presión contra incendios Dorot?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: UDS-2N (sim 0.51), CCD-103 (sim 0.44), UDS-1N (sim 0.50), CCD-103 (sim 0.43)
- Rationale judge: _El bot reconoce correctamente que no dispone de documentación sobre grupos de presión Dorot, describe con precisión los productos que sí cubre (Notifier, Detnov) sin inventar información técnica, y redirige al técnico a fuentes oficiales. La conducta observada coincide exactament..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### nd008  —  actualmente `expected_behavior: admit_no_info`

**Pregunta:** ¿Cómo doy de alta un lector en el control de acceso CDVI ATRIUM?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: VESDA-E VEA (sim 0.54), DBD-70A (sim 0.46), VESDA-E VEA (sim 0.54), DBD-70A (sim 0.45)
- Rationale judge: _El bot reconoce correctamente que ninguno de los fragmentos disponibles cubre el sistema CDVI ATRIUM y lo declara sin inventar procedimientos. La conducta observada (admit_no_info) coincide exactamente con la esperada, y la respuesta es honesta y relevante al redirigir al técnico..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---


## Categoría: `cross_manual` (8 preguntas)

### cm001  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Puedo usar un detector Notifier SDX-751 con una central Morley ZXe?

- Bot hizo: `answer`  ·  Judge: **PASS ✓**
- Chunks top: ZXe (sim 0.80), ZXe (sim 0.80), ZXe (sim 0.80), ZXe (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que los fragmentos disponibles no contienen información sobre el detector SDX-751 de Notifier ni sobre compatibilidad entre fabricantes, admite la limitación sin inventar datos, y orienta al técnico con pasos accionables concretos (verificar protocol..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm002  —  actualmente `expected_behavior: answer`

**Pregunta:** Necesito migrar de una Notifier AFP-200 antigua a una ID3000, manteniendo el cableado existente

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: AFP-200E (sim 0.82), AFP-200E (sim 0.82), AFP-200E (sim 0.80), AFP-200E (sim 0.80)
- Rationale judge: _El bot responde directamente (conducta 'answer') usando correctamente los fragmentos disponibles: cita terminales SLC de la AFP-200, estilos de cableado NFPA, detectores compatibles y módulos CMX con referencias verificables en los fragmentos. Reconoce honestamente que no tiene i..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm003  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Qué diferencias de comportamiento hay entre un detector óptico Detnov ASD531 y un Notifier SDX en condiciones de humedad alta?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: ASD531 (sim 0.85), ASD531 (sim 0.85), ASD531 (sim 0.85), ASD531 (sim 0.85)
- Rationale judge: _La conducta esperada era 'admit_no_info' porque ningún fragmento cubre el comportamiento en humedad del ASD531 ni existe ningún fragmento del Notifier SDX. El bot reconoce correctamente ambas carencias sin inventar datos, cita solo valores que sí aparecen en los fragmentos (75 mA..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm004  —  actualmente `expected_behavior: answer`

**Pregunta:** Comparar capacidad de lazos entre la Detnov CAD-150 y la Notifier ID3000

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: CAD-150-8 (sim 0.65), CAD-150-8 (sim 0.65), CAD-150-8 (sim 0.65), ID3000 (sim 0.65)
- Rationale judge: _El bot inventa datos concretos sobre la CAD-150-8 (los 5 modelos con configuraciones de lazos, capacidades de batería, ampliabilidad) citando [F3], pero el Fragmento 3 es simplemente el índice del manual y no contiene ninguno de esos datos técnicos. Ningún fragmento disponible so..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm005  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿Cómo configuro una red de centrales mezclando una Notifier ID3000 con una Morley DXc?

- Bot hizo: `admit_no_info`  ·  Judge: **PASS ✓**
- Chunks top: ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80), ID3000 (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que no tiene información sobre la Morley DXc ni sobre integración mixta entre fabricantes (admit_no_info para esa parte), pero aprovecha los fragmentos disponibles para informar sobre lo que sí cubre la documentación de la ID3000 (ID2net, límites de ..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm006  —  actualmente `expected_behavior: answer`

**Pregunta:** Tengo un módulo aislador Detnov en un lazo que comparte detectores Notifier. ¿Hay alguna incompatibilidad conocida?

- Bot hizo: `ask_clarification`  ·  Judge: **FAIL ✗**
- Chunks top: MAD-567 (sim 0.80), RP1r (sim 0.70), FAAST FLEX (sim 0.70), MAD-567 (sim 0.80)
- Rationale judge: _El bot inventa afirmaciones técnicas no respaldadas por los fragmentos: menciona terminales 3 y 4 para detectores con/sin aislador [F1], pero esa información no aparece en ninguno de los fragmentos recuperados. Además, la conducta esperada era 'admit_no_info' porque ningún fragme..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm007  —  actualmente `expected_behavior: answer`

**Pregunta:** ¿La base B501 de Notifier puede usarse con un detector Detnov serie 500?

- Bot hizo: `ask_clarification`  ·  Judge: **PASS ✓**
- Chunks top: B501RF (sim 0.80), B501RF (sim 0.80), B501RF (sim 0.80), B501RF (sim 0.80)
- Rationale judge: _El bot reconoce correctamente que los fragmentos solo cubren la B501RF (base inalámbrica para NRX-REP) y no la B501 cableada ni los detectores Detnov serie 500, admitiendo la falta de información sin inventar datos. La conducta es 'admit_no_info' para la pregunta concreta, lo cua..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---

### cm008  —  actualmente `expected_behavior: answer`

**Pregunta:** Pasos para reemplazar una Morley ZXe convencional por una ZXSe con detectores existentes

- Bot hizo: `answer`  ·  Judge: **FAIL ✗**
- Chunks top: ZXe (sim 0.65), ZXe (sim 0.65), ZXe (sim 0.65), ZXe (sim 0.65)
- Rationale judge: _El bot admite correctamente que los fragmentos no contienen información sobre el procedimiento de sustitución ZXe→ZXSe, lo cual es honesto y fiel a las fuentes disponibles. Sin embargo, 'helpful' es false porque aunque la conducta esperada es 'admit_no_info' y el bot la ejecuta c..._

**Tu verdict:** ☐ ✅ correcto  ☐ 🔄 cambiar a: ______________  ☐ ❓ dudoso

**Nota (opc):** 

---


## Resumen final (rellena cuando termines)

- Preguntas `correcto`: __ / 52
- Preguntas a `cambiar`: __ → lista de ids: _______________
- Preguntas `dudoso`: __ → lista de ids: _______________

Observaciones generales sobre patrones encontrados:
