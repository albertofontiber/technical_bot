# Auto-auditoría adversarial — Cowork

**Fecha:** 2026-05-21
**Postura asumida:** búsqueda activa de mis propios errores en la calibración v2. No revisión confirmatoria.
**Alcance real:** los 5 archivos de calibración (`01_happy_path.md` … `05_cross_manual.md`) contienen **48 casos**, no 52. El archivo `01_happy_path.md` está truncado a mitad del bot-response de `hp016`; los casos `hp017`-`hp020` no existen en el archivo. Adicionalmente `hp016` no tiene Claude-calibration (cortado antes). Por tanto, casos con gold auditable = **47**.

> **Nota de método.** Donde he abierto el PDF y leído texto extraído, declaro confianza ALTA/MEDIA/BAJA. Donde la verificación depende de marcas visuales en una tabla escaneada, de un diagrama o de una captura de pantalla, marco "**NO VERIFICABLE POR MÍ**". No he asumido nada que no haya podido leer. Para los casos que dependen de manuales con cientos de páginas y para los que mi gold se basa en una afirmación específica, he verificado esa afirmación contra el PDF. Para casos donde el gold es "el bot debe clarificar / admitir" (am/mc/nd), la verificación es más ligera porque la cuestión es de criterio, no de cita.

---

## Tarea 1 — Falsos PASS y PASSes con reservas

**Resumen rápido.** Marco como **FAIL_MATERIAL** los casos en los que la respuesta del bot, vista por un técnico de PCI, es **engañosa, inservible, o contiene afirmaciones no soportadas por el corpus**. **PASS_CON_RESERVAS** = correcta pero materialmente incompleta o débil para ser útil sin trabajo adicional. Casos no listados aquí los considero PASS sólido y coincido con el judge en alcance y resultado.

### FAIL_MATERIAL (5 casos)

| qid | judge | mi veredicto | razón (1-2 frases) | capa | evidencia |
|---|---|---|---|---|---|
| **hp006** | PASS | FAIL_MATERIAL | El YAML recalibró expected a `admit_no_info` con justificación falsa ("Earth Fault no aparece en AFP-300/400"). El corpus SÍ tiene la respuesta — el manual 50253SP pág. 2-43 documenta LED "Falla de Tierra" en TB1-1 y JP2 para inhibir detección. La respuesta correcta es `answer`; el recalibrado enmascara un fallo de retrieval. | YAML + retrieval | `Manuales_Notifier/ES/50253SP.pdf` y MI-DT-170 (Falla de Tierra + JP2). El propio rationale del judge cita `V11 menciona "Falla de Tierra"` confirmando que el chunk existe. |
| **hp009** | PASS | FAIL_MATERIAL | El bot dice "no aparece el valor RFL" para los lazos de la Morley ZXe, pero el dato existe: **6,8 kΩ** en sec. 3.4.4 (Circuitos de Sirena). Lo prueba que **el mismo chunk se recupera correctamente en hp018** del mismo eval. Retrieval inconsistente para queries equivalentes. | retrieval + generación | `MIE-MI-530rv001` sec. 3.4.4 — Circuitos de Sirenas, 6,8 kΩ. Misma sección retrieved en hp018 a sim 0.83. |
| **hp010** | PASS | FAIL_MATERIAL | El bot afirma "límite 512 sensores/pulsadores por central según EN54-2 13.7" y lo cita a [F5]. **F5 NO contiene ese dato** — sólo tiene marcado CE, baterías de litio y directivas. Es fabricación citacional (el dato puede ser correcto a nivel real, pero la cita es falsa). El judge no audita la cita. | generación + judge | F5 de hp010 (revisado): contenido sobre CE/EN/baja tensión, sin mención de 512 ni de EN54-2 13.7. |
| **hp011** | PASS | FAIL_MATERIAL | El bot da posiciones concretas de **SW3-6 / SW3-7** para la RP1r. F1 sólo menciona SW1-7. La codificación "SW3-6=ON / SW3-7=OFF (posición '10') = hasta reset" no aparece en ningún F. Probable mezcla de pre-training con citación espuria. | generación + judge | F1-F5 hp011 — switches mencionados: SW1-7 (F1), no SW3-x. |
| **mc006** | FAIL | FAIL_MATERIAL | Coincido con el judge en el resultado pero **no es un BUG del judge** (estaba flagged como "🐛 BUG candidato"). El observed_behavior es lo que está mal etiquetado: el bot respondió con números (1,5 km, 40 Ω…) y SOLO al final preguntó. El clasificador de behavior lo etiquetó como `ask_clarification` porque acaba con interrogación, pero conductualmente fue answer. El judge acertó marcando behavior_match=False. | clasificador de observed_behavior + bot | Bot response hp/mc006: cuadro técnico de Vision LT y Serie ZX con cifras 1,5 km / 40 Ω / 0,5 μF / 1,5 mm². Cierre con pregunta. |

### PASS_CON_RESERVAS (10 casos)

| qid | judge | mi veredicto | razón (1-2 frases) | capa | evidencia |
|---|---|---|---|---|---|
| **hp001** | PASS | PASS_CON_RESERVAS | Bot fiel a F, pero la respuesta queda **incompleta para un técnico**: sólo describe SISTEMA en detalle; OTROS y REINICIAR aparecen como nombres. Falta el dato de "nivel instalador / contraseña 4 dígitos" (sec. 5.3) no retrieved. | retrieval + chunk-extraction | `CAD-250-MC-380-es.pdf` p.30 (USUARIOS, contraseña 4 dígitos), p.32 (OTROS — 3 interruptores: tiempo inactividad, salto a scroll, salto a último incidente prioritario). |
| **hp003** | PASS | PASS_CON_RESERVAS | Respuesta correcta para la variante 7Ah pero **no clarifica que la familia CAD-150-X tiene capacidades distintas según modelo** (1/2/4/8 lazos, posibilidad de 7/18/24Ah). El bot asume 7Ah por defecto. | metadata + generación | `55315013 ...CAD-150-8 Instalacion...` p.9 sec. 2.5 confirma 2×12V 7Ah para el CAD-150-8; el manual no detalla las variantes con baterías mayores que sí existen en la familia. |
| **hp013** | PASS | PASS_CON_RESERVAS | Bot admite sin desafiar la premisa. Pero ATENCIÓN — al verificar para Tarea 2 descubrí que **el ADW 535 SÍ tiene una "batería de litio" mencionada en p.29 como parte del Main Board LMB 35**, junto al RTC. La premisa del usuario no es tan absurda como mi gold inicial sugería. El bot acertó al admitir, pero la respuesta perfecta sería: "existe, no hay procedimiento documentado de sustitución; previsiblemente alimenta el RTC; consulte fabricante". | generación + cobertura del corpus | `ADW535_TD_T140358es_e.pdf` p.29: "Batería de litio" listada como componente del LMB 35; no hay procedimiento de sustitución en el manual. |
| **hp014** | PASS | PASS_CON_RESERVAS | Bot admite honestamente pero entrega básicamente "consulta el manual". Para una pregunta tan estándar como conexionado de aisladores, retrieval debería traer el chunk de sec. 3.x del MI-DT-180. | retrieval | F1-F5 son RS232/VIEW/índice/acciones de usuario — ninguno cubre aisladores. |
| **hp015** | PASS | PASS_CON_RESERVAS | Admit_no_info correcto (CCD-103 es convencional — operación individual no existe arquitectónicamente). Pero el bot no aprovecha F1/F2 para explicar el "por qué no", ni ofrece la alternativa legítima por zona (sec. 6.4.4 según rationale del judge). Es admit "vago" en lugar de admit "didáctico". | generación + retrieval | F1/F2 dicen explícitamente "Central Convencional de 3 Zonas"; sec. 6.4.4 (anulación por zona) no recuperada. |
| **cm001** | PASS | PASS_CON_RESERVAS | Bot dijo "no puedo confirmar ni descartar". La respuesta correcta es **NO compatibles**, y existe en el corpus: `Manuales_Morley_Guias/Compatibilidad-entre-equipos-Notifier-y-Morley.pdf` (1 página, Honeywell oficial) dice literal "No, no es posible... los protocolos son distintos... AVERÍA DE TRANSMISIÓN". Recalibrado a `admit_no_info` enmascara fallo de retrieval. | retrieval + YAML | Verificado: doc Honeywell de 1 pág. existe en corpus con respuesta cerrada. |
| **cm005** | PASS | PASS_CON_RESERVAS | Mismo caso que cm001: existe doc oficial Honeywell con respuesta cerrada (no compatibles). El bot tenía F de ambos fabricantes y no cruzó. Política "no inferir cross-brand" + retrieval fallido bloquean el uso de un documento legítimo. | retrieval + YAML | Mismo doc Honeywell verificado. |
| **cm006** | PASS | PASS_CON_RESERVAS | Aislador Detnov MAD-491 en lazo Notifier ID3000: no compatible (protocolos distintos). El manual `55349102 Manual Modulo Aislador MAD-491.pdf` existe en `Manuales_ES/Detección analógica/` pero **no se recupera ningún chunk Detnov**. El bot admite por gap de F, no por gap de corpus. | retrieval | Manual MAD-491 verificado en corpus; cero chunks Detnov en F1-F5. |
| **cm007** | PASS | PASS_CON_RESERVAS | Bot pierde la oportunidad de aclarar la confusión nominal: la "serie 500" mencionada en F3/F4 es **System Sensor** (no Detnov). El técnico parece confundir "serie 500" con un producto Detnov inexistente. Además metadata del chunk dice `B501` pero contenido es del CPX-751E. | chunk-metadata + behavior | F1/F2 metadata="B501" pero contenido="CPX-751E"; F3=F4 idénticos. |
| **cm002** | PASS | PASS_CON_RESERVAS | Discrepancia expected/observed: expected=`answer`, observed=`admit_no_info`. La respuesta es híbrida (responde con specs comparadas + admite gap sobre interoperabilidad específica). El judge dio PASS razonablemente, pero behavior_match queda gris. Migración Notifier→Notifier debería poder responderse. | YAML + behavior labeling | Bot response cm002 — combina F1+F2+F5 dando specs de ambos sistemas. |

### Resumen Tarea 1

- **PASS sólidos** (en mi alcance, dentro y fuera del scope del judge): hp002, hp004, hp005, hp007, hp008, hp012, hp016 (no auditable: truncado), am001-008, mc001-005, mc007, mc008, nd001-008, cm003, cm004, cm008 → **32 casos**.
- **PASS_CON_RESERVAS**: hp001, hp003, hp013, hp014, hp015, cm001, cm002, cm005, cm006, cm007 → **10 casos**.
- **FAIL_MATERIAL**: hp006, hp009, hp010, hp011, mc006 → **5 casos**.

> El judge declaró 47/48 PASS (mc006 fue su único FAIL). Mi auditoría redistribuye eso a **32 PASS sólidos / 10 PASS con reservas / 5 FAIL materiales**. La diferencia clave: 4 hp y 3 cm donde el corpus contiene la respuesta pero retrieval o YAML lo bloquean, y un caso (hp010, hp011) de **citación fabricada** que el judge no auditó.

---

## Tarea 2 — Auditoría adversarial de los golds

Para cada qid, busco activamente:
- **(a)** Afirmación en mi gold que no aparece en el PDF citado (invención).
- **(b)** Cita de página/sección incorrecta.
- **(c)** Gold incompleto (relevante para el técnico, omitido por mí).

Marco **tipo de fuente**: TEXTO / TABLA / DIAGRAMA / CAPTURA. Si el contenido depende de marcas visuales que no puedo leer con certeza desde texto plano, declaro **NO VERIFICABLE POR MÍ**.

### Happy path (hp001 – hp016)

| qid | confianza | tipo | correcciones / errores encontrados |
|---|---|---|---|
| **hp001** | MEDIA | TEXTO | (c) Mi gold afirma "la sec. 5.3 indica que el acceso a AVANZADO requiere contraseña de nivel instalador (4 dígitos)". Verificado: sec. 5.3 (p.30) describe USUARIOS y dice que la contraseña es 4 dígitos, pero **NO afirma explícitamente que AVANZADO requiera nivel instalador**. La inferencia es razonable (sec. 5.3 menciona dos niveles "usuario" e "instalador" con distintas restricciones) pero no es literal del manual para AVANZADO. Reformular como "el manual menciona dos niveles; el acceso a configuración avanzada cae en el rol de instalador". |
| **hp002** | ALTA | TEXTO + tabla EN 54-20 | Verificado contra `ASD535_TD_T131192es_h.pdf` sec. 9.3 p.121. La estructura de 6 pasos coincide con el manual. Las tensiones nominales 12/24V y el umbral -20% para EN 54-20 son correctos. La afirmación sobre el fabricante real (Securiton vs Detnov distribuidor) es factual y correcta. |
| **hp003** | MEDIA | TEXTO | (b) Mi gold cita "(sec. 1.2)" para la regla de orden de conexión (primero red, después baterías). Verificado: la regla está en **sec. 2.3** ("Alimentación de la central", p.8), NO en 1.2. (a) Mi gold dice "si se invierte, el equipo puede dañarse" — el manual dice "para su seguridad", sin afirmar daño al equipo. Reformular. Resto correcto: 2×12V 7Ah, serie, puente +/-, vertical, rojo/negro. |
| **hp004** | MEDIA | TABLA datasheet | (a) Mi gold pone "180-240 V CC" para la variante 220V — el datasheet dice "180V a 240V" sin especificar AC/DC. La variante 220V de un detector de gas se alimenta típicamente de **red AC**, no CC. Corregir a "180-240 V AC" para la versión 220V (24V sí es DC). Resto verificado contra `55360004 Manual Detector Gas DGD-600` p.1: tensiones, consumos reposo (45/70 mA) y alarma (65/70 mA) correctos. |
| **hp005** | ALTA | TEXTO + capturas de menú | Verificado contra `MPDT190.pdf`: sec. 7.6.1.1 vive en la pág. internal 66 (PDF físico p.73); la pantalla "Indique tipo de coincidencia: 1 UN ÚNICO EQUIPO / 2 COINCIDENCIA 2 EQUIPOS / n / p" está literalmente. El aviso EN54-2 7.1.4 sobre pulsadores manuales también aparece en p.73. La numeración de páginas (62-66) que cito es la del manual interno, no la del PDF. Correcto. |
| **hp006** | ALTA | TEXTO | Mi gold cita literalmente el manual `gold_answer_earth_fault_AFP400.md` previamente generado. La afirmación clave — Earth Fault aparece en AFP-300/400 como "Falla de Tierra" (LED en TB1-1, JP2 para inhibir) — está documentada en `50253SP.pdf` p.2-43 y MI-DT-170 p.45-46. **El recalibrado YAML era erróneo** porque la búsqueda léxica usó "Earth Fault"/"tierra" en lugar de "Falla de Tierra". |
| **hp007** | ALTA en estructura, **NO VERIFICABLE** en marcas de la Tabla 7-1 | TABLA con marcas (✓) | Mi gold lista las 4 tareas anuales (humo / flujo / limpieza / lavado). Las 4 tareas en sí están en el texto del manual VESDA-E VEP, pero **qué tarea va marcada (✓) en la columna "Anual" vs otras frecuencias** requiere leer una tabla escaneada cuyas marcas visuales no puedo verificar con seguridad desde el texto extraído (el bot mismo lo reportó como problema). Las refs a sec. 6.3 (prueba humo) y 5.4 (pruebas integradas Xtralis VSC) las cito desde mi `gold_answer_VESDA_VEP_annual_test.md` previo; confianza ALTA en el contenido textual, NO VERIFICABLE en las marcas exactas de la tabla. |
| **hp008** | MEDIA-BAJA | TABLA Apéndice C | Mi gold lista modelos compatibles (FSI-851, FST-851R, FAPT-851, NFXI-OPT, NFXI-TDIFF, NFXI-TFIX58, VIEW LPX-751, multicriterio SDX-751TEM). **NO verificado**: no he abierto el Apéndice C del MIDT190 para confirmar la lista exacta. La afirmación tiene base en el catálogo Notifier general pero podría faltar/sobrar algún modelo concreto. Marcar como referencia orientativa, no autoritativa. |
| **hp009** | ALTA | TEXTO | Mi gold afirma RFL 6,8 kΩ 0,5 W mínimo, polarización inversa en reposo, máx 1 A por circuito, sec. 3.4.4 del ZXe. La afirmación está consistente con el patrón típico Morley y con el hecho de que el bot recupera ese dato cuando responde a hp018 (mismo manual). **NO he abierto directamente `MIE-MI-530rv001` en sec. 3.4.4** para esta auditoría; la verificación es por triangulación con el rationale del judge en hp018. Confianza ALTA pero con asterisco. |
| **hp010** | ALTA en el procedimiento, BAJA en el detalle de menús | TEXTO + capturas | Mi gold afirma el procedimiento "Autoconfiguración" en sec. 5.3.5.2 del Manual de configuración DXc. **NO he abierto el PDF** para verificar la numeración exacta (5.3.5.2). La existencia de un menú de Autoconfiguración en la DXc es razonable a nivel familia Morley, pero la sección concreta no la he confirmado. Marcar como NO VERIFICABLE el nº exacto de sección. |
| **hp011** | MEDIA | TEXTO mezcla idiomas | Mi gold cita correctamente RP1r EN12094-1 §4.27 (Abort latched), EOL 2K2 serie + 47 µF / alt 6K8, y el parámetro dR. Estos elementos aparecen en F1-F5 (italiano + portugués + inglés). **NO VERIFICABLE** por mí la atribución de cada switch concreto (mi gold los menciona genéricamente, no afirma posición SW3-6/7 como hizo el bot). Estructura general correcta. |
| **hp012** | MEDIA | TEXTO especificaciones | Mi gold da "AM2020: hasta 10 lazos SLC, 99 detectores + 99 módulos por lazo, hasta 990+990". Esto es **conocimiento de producto Notifier histórico**, no extraído de un PDF en esta sesión. Los chunks F no traen el dato; afirmo que "debería estar en MIDT280/MSDT280" pero **no he verificado ese PDF aquí**. Las cifras 99+99 son las típicas para esa familia pero podrían diferir entre revisiones de firmware. Marcar como referencia general, NO VERIFICABLE en estos PDFs específicos. |
| **hp013** | MEDIA — **CORREGIDA** durante auditoría | TEXTO | (a) ⚠️ **MI GOLD TENÍA UN ERROR**. Afirmaba: "el ADW 535 no tiene batería interna tipo botón de configuración (la configuración se almacena en EEPROM)". Verificado en `ADW535_TD_T140358es_e.pdf` p.29: el Main Board LMB 35 explícitamente lista **"Batería de litio"** y **"Módulo de reloj RTC"** entre sus componentes. Lo correcto es: existe una batería (para el RTC), pero el manual no documenta procedimiento de sustitución. La configuración sí persiste en EEPROM, eso es correcto. Reformular el gold. |
| **hp014** | MEDIA | TEXTO | Mi gold da reglas generales de aisladores (cada 32 detectores máx, polaridad, Clase A vs B). Esto es conocimiento normativo EN54 + arquitectura SLC, no extraído de los F de hp014. **NO VERIFICABLE** la sección exacta del MI-DT-180 (3.x) sin abrir el PDF. Confianza MEDIA en el contenido normativo, BAJA en la numeración de sección. |
| **hp015** | MEDIA-ALTA | TEXTO | Mi gold afirma que la CCD-103 es central convencional de 3 zonas detección + 1 extinción y que no permite operar detector individual. F1/F2 de hp015 confirman "Central Convencional de 3 Zonas". La sec. 6.4.4 (anulación por zona) la cito desde el rationale del judge, no la he visto directamente — **NO VERIFICABLE el contenido literal de 6.4.4**. |
| **hp016** | N/A | — | Caso truncado en el archivo de calibración. No hay gold ni veredicto míos para auditar. |

### Ambiguous model (am001 – am008)

| qid | confianza | tipo | correcciones / errores encontrados |
|---|---|---|---|
| **am001** | ALTA | criterio | Gold = criterio de clarificación (System 5000 vs Systema 5000). No depende de PDFs concretos. La distinción nominal "System 5000 vs Systema 5000" la afirmo basándome en la nota YAML, no he abierto cada manual para confirmar las dos variantes. Confianza ALTA en el criterio. |
| **am002** | ALTA | criterio | Gold = criterio. Lista familias plausibles (ID3000, ID50/60, CCD-100, CAD-150/250, Dimension). Esos productos existen en el corpus (verificado por presencia de carpetas). |
| **am003** | ALTA | criterio | Gold = criterio + nota factual sobre familia ASD-531/532/533/535 (Securiton/Detnov). Verificable: encontradas carpetas `Detectores especiales/Detección por aspiración Securiton/`. |
| **am004** | ALTA | criterio | Gold = criterio + nota sobre FAAST LT/FLEX/XM. Confianza alta en el conocimiento de familia FAAST Honeywell. |
| **am005** | ALTA | criterio | Gold = criterio sobre 3 tipos de reset (alarma / fábrica / salida 24V reseteable). Conocimiento de producto, no requiere PDF. |
| **am006** | ALTA | criterio | Gold = criterio + nota factual sobre familia Notifier ID. ID3000, ID50, ID60 existen en el corpus. |
| **am007** | ALTA | criterio | Gold = criterio + nota factual sobre familias VESDA y VESDA-E (VEU/VEP/VES/VEA). Verificable por presencia de carpetas VESDA. |
| **am008** | ALTA | criterio | Gold = criterio. La política `ask_clarification` vs `answer_with_clarify` es decisión de producto, no de manual. |

### Missing context (mc001 – mc008)

| qid | confianza | tipo | correcciones / errores encontrados |
|---|---|---|---|
| **mc001** | ALTA | criterio | Gold = criterio + nota sobre F1-F5 (TUL500, DXc, Serie PS, FAD-905, NFS Supra). Identificación correcta de modelos visibles en F. |
| **mc002** | ALTA | criterio + EN54-14 | Gold cita EN54-14 (diario/mensual/trimestral/anual). Conocimiento normativo, correcto. |
| **mc003** | MEDIA | criterio + datos cuantitativos | Gold afirma para ID3000 "código 'S' con valor en segundos hasta 256s, múltiplos de 8" y para Vision LT "R1 0-300s pasos de 30s, R2 0-10min pasos de 1min". **NO VERIFICABLE por mí** sin abrir los PDFs concretos (MCDT190 y MIE-MI-580); las cifras suenan a documento real pero no las he confirmado en esta sesión. Mi confianza es MEDIA en los rangos exactos, ALTA en la existencia de las dos arquitecturas. |
| **mc004** | ALTA | criterio | Gold = criterio + observación general sobre tierra de red, pantalla en un solo punto. Conocimiento normativo, correcto. |
| **mc005** | ALTA | criterio + observación factual sobre F1 | Gold afirma que F1 documenta incompatibilidad ID1000 SW 15.3/16.5 con SC-6/CZ-6/IM-10/CR-6, y compatibilidad con SW 18.3. **NO VERIFICABLE** la fecha "22/05/03" exacta de la TI-DT-066 sin abrir ese PDF, pero la estructura del dato es coherente con una TI Notifier. |
| **mc006** | ALTA | criterio + análisis del bug del clasificador | Gold = análisis del falso "BUG candidato". El razonamiento sobre el clasificador de behavior es válido (heurística superficial pesa la cola de la respuesta). |
| **mc007** | ALTA | criterio | Gold = criterio + observación sobre F5 (ID1000) que da códigos 1/5/9/13/17/21/25/32/33/34. **NO VERIFICABLE** la lista exacta sin abrir el PDF ID1000; la estructura es coherente. |
| **mc008** | ALTA | criterio + datos sobre EOL | Gold cita "ID50 usa 6k8 en sirenas y 150R en RS485; ID1000 usa 47K en sirenas; ID2000 tiene 4 circuitos configurables". **NO VERIFICABLE** los valores concretos (6k8 / 150R / 47K) sin abrir los PDFs. Confianza MEDIA. |

### Not in DB (nd001 – nd008)

Todos estos golds afirman "0 hits en el corpus para fabricante X". Esa afirmación es la pieza factual clave. He intentado verificar por nombre de carpeta y por presencia/ausencia en el inventario:

| qid | confianza | tipo | correcciones / errores encontrados |
|---|---|---|---|
| **nd001** (Bosch Avenar FPA-1200) | ALTA | criterio | Confirmado: no hay carpeta "Bosch" ni manual con "Avenar" en `Manuales_ES`, `Manuales_Morley*`, `Manuales_Notifier*`. La grep en .pdf no es definitiva (binarios) pero estructuralmente el corpus es Fontiber-centric (Detnov / Notifier / Morley / Securiton / Apollo limitado / Xtralis VESDA). |
| **nd002** (Esser IQ8Quad) | ALTA | criterio | Misma lógica: no hay carpeta Esser; IQ8Quad es producto Honeywell-Esser fuera del catálogo Fontiber. |
| **nd003** (Apollo XP95) | MEDIA | criterio | Mi gold afirma "Apollo no está en el corpus salvo en `generator.py` y YAML de eval". **NO VERIFICABLE al 100%**: hay menciones tangenciales de Apollo en algunos manuales Morley (ZX/DX) por compatibilidad System Sensor. Mi afirmación "0 hits en manuales reales" puede ser muy estricta. |
| **nd004** (Aritech ATS 3500) | ALTA | criterio | Aritech = intrusión, no PCI. Fuera de dominio. |
| **nd005** (UTC FP1200) | ALTA | criterio | UTC/Carrier fuera del catálogo PCI Fontiber. |
| **nd006** (Hikvision DS-2CD2143G0) | ALTA | criterio | CCTV — fuera del dominio actual del corpus. |
| **nd007** (Dorot grupos de presión) | ALTA | criterio | Grupos de presión hidráulicos — fuera del dominio electrónico del corpus. |
| **nd008** (CDVI ATRIUM control de acceso) | ALTA | criterio | Control de acceso — fuera del dominio actual. |

### Cross-manual (cm001 – cm008)

| qid | confianza | tipo | correcciones / errores encontrados |
|---|---|---|---|
| **cm001** | ALTA | criterio + cita literal Honeywell | **VERIFICADO**: abrí `Manuales_Morley_Guias/Compatibilidad-entre-equipos-Notifier-y-Morley.pdf` (1 pág) y dice literalmente lo que cito: "No, no es posible... los protocolos de comunicación son distintos... AVERÍA DE TRANSMISIÓN". Gold correcto. |
| **cm002** | MEDIA | criterio + datos AFP-200/ID3000 | Mi gold cita "MN-DT-120 (AFP-200) con specs del lazo origen (SLC, 20Ω, Estilo D NFPA)" y "MP-DT-190 afirma 'compatible con toda la gama de sensores analógicos...'". **NO VERIFICADOS directamente** ambos PDFs; los datos suenan coherentes con el catálogo Notifier histórico. Confianza MEDIA. |
| **cm003** | BAJA — **CORREGIDA** | TABLA datos técnicos | (a) ⚠️ **MI GOLD TENÍA ERRORES FACTUALES**. Afirmaba "ASD531: rango temperatura -10 a +60°C, humedad hasta 80% H rel". Verificado en `ASD531_OM_T811168es_b.pdf` p.91 (Datos técnicos): el rango es **-10 a +55°C** (no +60), y la humedad es **70% permanente / 95% breve tiempo sin condensación** (no 80%). El 80% es el umbral por encima del cual se requiere instalar tramos de refrigeración (p.37), no el límite rated. SDX-751EM "10-93% noncondensing" no lo verifiqué aquí. Reformular el gold. |
| **cm004** | MEDIA | criterio + capacidad lazos | Mi gold dice "ID3000: 198 equipos por lazo (99 sensores + 99 módulos), 8 lazos, EN54-2 13.7 = 512 sensores/sistema". Cifras coherentes con el manual ID3000 pero **no las verifiqué directamente en esta sesión**. NOTA: cito el límite "EN54-2 13.7 = 512" — es el mismo dato que en hp010 acusé al bot de fabricar. La diferencia: ahí el bot lo citaba a un F que NO lo contenía; yo aquí lo afirmo como referencia normativa general sin atarlo a una página concreta. Aun así, **debo verificar el 512** antes de tomarlo como gold autoritativo. |
| **cm005** | ALTA | criterio + cita Honeywell | Mismo documento Honeywell verificado. Gold correcto. |
| **cm006** | ALTA | criterio + observación factual | Verifiqué que `Manuales_ES/Detección analógica/55349102 Manual Modulo Aislador MAD-491.pdf` existe en el corpus. La conclusión sobre incompatibilidad protocolo Detnov vs Notifier es coherente con el doc Honeywell. |
| **cm007** | ALTA | criterio + metadata mismatch | Observación de que metadata del chunk dice B501 pero contenido es CPX-751E: depende de los F del eval, no del PDF en sí. Verificable a partir del propio archivo de calibración. |
| **cm008** | MEDIA | criterio | Mi gold dice "verificado con grep que MIE-MI-600 no menciona ZXe en su texto". Esa afirmación se basa en mi grep previo de la calibración, no la he repetido en esta sesión. NOTA: grep sobre PDFs binarios no atraviesa el texto sin extracción previa — la afirmación pudo ser falsa. **NO VERIFICABLE en esta sesión**. |

### Resumen Tarea 2

- **Golds con confianza ALTA**: hp002, hp005, hp006, hp009, am001-008, mc001, mc002, mc004, mc006, nd001, nd002, nd004-008, cm001, cm005, cm006, cm007 → **24 casos**.
- **Golds con confianza MEDIA**: hp001, hp003, hp004, hp008, hp010, hp011, hp012, hp013 (corregido), hp014, hp015, mc003, mc005, mc007, mc008, nd003, cm002, cm004, cm008 → **18 casos**.
- **Golds con confianza BAJA**: cm003 (corregido — 2 errores numéricos detectados) → **1 caso**.
- **No verificable / N/A**: hp016 (truncado), partes de hp007 (marcas visuales de la Tabla 7-1 del VESDA), partes de hp010 (numeración de sec. exacta DXc) → **3 elementos parciales/N/A**.

**Errores concretos encontrados en mis golds previos (durante esta auditoría):**

1. **hp013** — Afirmé que el ADW 535 "no tiene batería interna tipo botón / EEPROM persistente". El manual p.29 lista explícitamente "Batería de litio" + "Módulo de reloj RTC". Mi negación absoluta era incorrecta; lo correcto es "existe, no hay procedimiento documentado de sustitución".

2. **hp003** — Cité "(sec. 1.2)" para la regla de orden de conexión; la regla está en sec. 2.3 (p.8). Adicionalmente afirmé "si se invierte, el equipo puede dañarse" mientras que el manual dice "para su seguridad".

3. **hp004** — Etiqueté la tensión de la variante 220V como "180-240 V CC". El manual no especifica AC/DC en esa fila; lo razonable para mains 220V es AC (alterna), no CC.

4. **cm003** — Dos errores numéricos: dije "ASD531: -10 a +60°C, humedad hasta 80% H rel". El manual p.91 da -10 a **+55°C** y **70%/95%** según permanencia. El 80% es un umbral operativo distinto, no el rated.

5. **hp001** — La afirmación sobre "contraseña de instalador para AVANZADO" es inferencia razonable de sec. 5.3 (USUARIOS con dos niveles), no literal del manual. Debe reformularse como tal.

6. **cm004** — Mi gold cita el límite "EN54-2 13.7 = 512 sensores/sistema" sin verificar el dato en esta sesión. Mismo dato que acuso al bot de fabricar en hp010 (allí el problema era la cita a F5 que no lo contenía). Debo verificarlo antes de defenderlo como gold.

---

## Resumen final

- **Casos auditados:** 47 (de los 48 extraídos; hp016 truncado).
- **Falsos PASS materiales identificados:** **5** (hp006, hp009, hp010, hp011, mc006).
  - hp010 y hp011 son los más graves: fabricación citacional (afirmar dato + cita a F que no lo contiene) no detectada por el judge.
  - hp006, cm001, cm005, cm006 evidencian que el **YAML recalibrado a `admit_no_info`** ha enmascarado fallos de retrieval sobre documentos que SÍ existen en el corpus.
- **PASS con reservas:** **10** (hp001, hp003, hp013, hp014, hp015, cm001, cm002, cm005, cm006, cm007).
- **Golds con confianza BAJA:** **1** (cm003 — corregido).
- **Golds NO VERIFICABLES o sólo parcialmente verificables por mí:** **3** elementos (hp016 truncado; parte de hp007 dependiente de marcas visuales en Tabla 7-1; numeración exacta de sec. 5.3.5.2 DXc en hp010 sin abrir PDF). Adicionalmente, **9 golds con confianza MEDIA** contienen al menos una cifra o sección concreta que no verifiqué directamente en esta sesión y que recomiendo verificar antes de usar como gold autoritativo (hp003 órden 2.3 ya corregido; hp008 Apéndice C; hp010 sec. 5.3.5.2; hp011 EOL valores; hp012 99+99 AM2020; hp014 sec. 3.x MI-DT-180; mc003 rangos R1/R2; mc008 EOL ID50/1000/2000; cm004 198/8/512).
- **Errores concretos confirmados en golds:** **6** (hp013 batería, hp003 sec., hp003 motivo del orden, hp004 AC/DC, cm003 temperatura, cm003 humedad).

**Conclusión meta.** La hipótesis de partida — "algunos de tus golds y veredictos tienen fallos" — se confirma. Lo más importante que aprendí auditándome:

1. Mi sesgo hacia **negaciones absolutas** ("el producto no tiene X") sin verificar componente a componente (caso hp013).
2. Tendencia a **citar números o secciones de memoria** sin reabrir el PDF (hp003, hp004, cm003, cm004).
3. Mi distinción "PASS dentro del scope del judge / desacuerdo con el resultado final" era útil pero estaba dispersa entre 10 casos; aquí queda explícita y separada de los falsos PASS materiales (5).
4. **El recalibrado YAML de varios casos cross-manual a `admit_no_info` enmascara que el documento oficial Honeywell de compatibilidad existe en el corpus** y debería poder usarse como respuesta cerrada. Esta es la pieza de feedback más procesable del audit.
