# Lo que espera tu decisión — al cierre de s336 (21-ago-2026)

> **Tu pasada del packet v3 lo cerró entero**: anotaste las **56 filas vivas** (34 decisiones
> distintas). No queda ninguna fila del packet E1 esperándote. Lo que sigue son **cinco cosas**, y
> tres de ellas son una frase.
>
> Cada punto trae la medida ya hecha, para que decidas con el dato delante sin abrir nada.
> El detalle fila a fila está en `evals/s331_derivacion_pasada_alberto_v1.md`.

---

## 🟢 Tres frases

### 1. Paraguas «2X-A» — **con o sin los táctiles**

Tu OK era condicional: *«¿tenemos algún manual que sea "Guía de instalación rápida de la serie
2X-AT"? si no, OK a 2X-A»*.

**Respuesta: SÍ, tenemos dos, los dos en español.**
`00 3280 508 4109 06 r006 2x at series quick start guide` y
`00 3280 508 4209 02 r002 2x at series quick operation gu`.

O sea que la condición **no** se cumple y la pregunta sigue viva: **¿el paraguas «2X-A» lleva dentro
los 11 modelos táctiles (38 en total) o no (27, porque «2X-AT» ya tiene paraguas propio)?**

**Medido** (`evals/s331_2xa_sonda_plan_v1.json`): 0 gold perdidas · 2 golds ganan 12 fuentes cada una
—una es «¿El detector KE-DP3020W vale para la central 2X-A?»— · 0 disparos en 111 consultas reales.

👉 *Una frase y lo aplico con recibo; de paso caen 4 documentos de la serie que hoy están sin
`doc_map` esperando esto.*

### 2. EFS/EM 8 — **qué marca es la canónica**

Dijiste OK a las dos filas (`morley:efs-em-8` y `notifier:efs-em-8`), que es coherente con **R3**:
`MS8` y `FS8` son **el mismo manual** (código `997-201-103`, misma edición) archivado bajo las dos
marcas. Pero un producto tiene **un** id inmutable y el otro se modela como redirect.

**Propongo** canónico `notifier:efs-em-8` (es Notifier quien lo publica hoy, en `manualesobs`) con
`morley:efs-em-8` → redirect, y `vendido_bajo` = ambas.

👉 *Si lo prefieres al revés, dilo y ya está. Si no dices nada, aplico lo propuesto.*

### 3. WMSOU — **la gama, o esperar a los SKU**

Me pediste confirmar tu hipótesis sobre `D838-1_kac sounders`. **Confirmada, y con margen amplio.**

Las **ocho** especificaciones del documento coinciden **literalmente** con la hoja publicada de la
gama WMSOU de System Sensor Europe (15-32 VDC sin aislador / 15-28 con aislador · <6,81 mA ·
100 dB(A) ±3 · −25 a +70 °C · 95% sin condensación · IP24/IP65 · 2,5 mm²), incluido el mismo pie
«System Sensor Europe, Units 15-19 Trescott Road, Redditch». Y **no** coinciden con las de sus
hermanos rebrandeados: el KAC `WSO-` y el Notifier Opal `NFX-WS-` dan **95 dB(A)** e **IP21C/IP44**.
El propio documento cubre las **dos** variantes —imprime los dos rangos de tensión—, que es
exactamente el corte `P01` (sin aislador) / `P02` (con aislador).

**El matiz que tu fuente no traía**: el nombre del fichero dice «kac sounders» y el código del
documento es `D838 issue 1`, mientras que la hoja WMSOU publicada es `D800 issue 8`. El **hardware**
es el mismo; el número de documento es de otra tirada. Es tu propia R8 en versión fuerte: **el
nombre del fichero también miente sobre la marca**, no sólo sobre la grafía.

**Lo que no puedo hacer solo**: el documento **no imprime ningún sufijo de color** (`-RR` / `-WW`).
Dar de alta los cuatro SKU sería inventar cuatro tokens que no aparecen en el corpus.

👉 **Propongo** dar de alta la **gama** `systemsensor:wmsou` y esperar a un documento que enumere los
SKU. ¿De acuerdo, o los quieres los cuatro igualmente?

---

## 🟡 Dos decisiones de fondo

### 4. `accessory-of` — **un cambio de esquema que tú tienes que autorizar**

Dos filas que ya adjudicaste están **bloqueadas por lo mismo**:

- `kidde:ke-dba-sktw` — *«el producto es el KE-DBA-SKTW, pero es un accesorio del producto
  KE-DB3010W»*
- `spectrex:40-40-air` — *«esto parece un accesorio (Air shield) del producto 40/40 […] asócialo a
  la familia 40/40»*

`relations.jsonl` admite hoy `variant-of | rebrand-of | shared-doc | supersedes`. **No tiene
`accessory-of`.** Sin ese tipo, el alta se puede hacer pero la relación no, y un accesorio suelto no
sirve para nada: «¿esta falda vale para mi base?» no tiene respuesta sin el padre.

Fíjate además en que los dos casos son **distintos**: uno cuelga de un MODELO y el otro de una
FAMILIA entera («can be used with all Spectrex 40/40 series flame detectors», tu enlace de Emerson).
El tipo tiene que admitir las dos cosas.

👉 *¿Lo añado? Es medio/alto → va con dúo y gate. Si dices que sí, lo llevo la próxima sesión.*

### 5. Los 5 documentos FAAST atribuidos a Xtralis — **sigue abierto de anoche**

De los 30 documentos activos que mencionan FAAST: 19 Notifier (bien), 5 Morley (bien),
1 System Sensor (bien) y **5 Xtralis**, que es el fabricante de VESDA, o sea **la competencia**.

No lo he parcheado a propósito: el dúo señaló que sería otro parche efímero mientras
`TECH_DEBT #97` siga abierto (los retags de `manufacturer` no son persistentes — una re-ingesta los
deshace en silencio). Las tres rutas medidas siguen sobre la mesa; la decisión es tuya.

---

## 🔴 Manuales huérfanos → **este bloque se mudó**

El detalle vivía aquí y se quedaba desfasado cada vez que avanzaba el trabajo (llegó a decir
«245 → 134» cuando ya iban 82). Dos documentos con la misma cola, uno mal, es peor que uno solo.

👉 **La cola canónica de huérfanos es [`REVISION_ALBERTO_HUERFANOS.md`](REVISION_ALBERTO_HUERFANOS.md)**:
82 huérfanos en 22 decisiones, una fila = una decisión, con recomendación y evidencia. Se
**regenera** con `python scripts/s337_packet_revision_alberto.py` sobre el catálogo vivo, así que
no puede quedarse viejo mientras alguien lo regenere.

### Ya lo cerraste — y esto es lo que quedó vivo (s339, 22-ago)

Terminaste el packet: **23 de 24 casillas y 46 anotaciones**. Traducidas a lote, medidas y pasadas
por la puerta: **huérfanos 82 → 25**, `validate` limpio, **0 gold perdidas**, 0 disparos en
negativos sintéticos, **4 golds ganan fuentes**, y una batería nueva derivada de los propios
términos del lote da **30/30 positivos y 5/5 negativos**. El lote NO está aplicado: espera tu OK.

**Dos cosas que hice distinto de lo que escribiste, y por qué:**

1. **§5.1 — no puedo BORRAR `notifier:notifier-inspire-e10`.** Pediste llamarlo directamente
   `notifier:inspire-e10` «para evitar tener los dos nombres en la BD via redirect». El contrato de
   identidad lo prohíbe en una línea: *«Los ids son INMUTABLES: nunca se borran ni se reciclan»*, y
   para un merge prescribe `redirect`. Y el id está referenciado en 4 entradas de `doc_map` y 1
   alias, así que borrarlo rompería lo ya etiquetado. **El redirect te da lo que querías**: deja de
   existir como producto consultable —no sale en inventarios ni resuelve como fila propia—, sólo
   reenvía. De cara al bot no hay dos nombres; hay un puntero interno que evita romper el pasado.

2. **§6.3 NAS — tu adjudicación de producto es correcta y está aplicada; la del NOMBRE la cambié.**
   NAS existe, es el Notifier Air Sample, y el id es `notifier:nas` como dijiste. Pero
   *producto-hood* y *detectabilidad* son preguntas distintas y yo las tenía juntas. Medido: el
   token «NAS» dispara en los tres negativos — «insira os condutores **nas** respectivas portas»
   (preposición portuguesa, que está literal en el corpus), la misma intercalada en español, y «un
   **NAS** de red» (Network Attached Storage). Es DEC-272 otra vez. `DETECT_STOPWORDS` no sirve:
   es una lista global y mataría NAS del todo. Así que el **canónico** pasa a «Notifier Air
   Sample», que es como TÚ describes el producto; el id no se toca. Los manuales dejan de ser
   huérfanos igual y el token corto ya no dispara.
   👉 **Si quieres «NAS» alcanzable pese a los falsos positivos, dilo: es añadir un alias.**

### 🔴 Lo que sigue esperándote — 9 puntos

| # | qué | por qué no lo decido yo |
|---|---|---|
| 1 | **`desico:tg-1020`** — ¿atribución equivocada, homónimo, o se queda? | Es la pregunta del final del packet, sin marcar. Ahora **bloquea de verdad**: promover `notifier:tg-1020` choca con él y `validate` lo caza como canónico duplicado. Sin tu línea, TG-1020 se queda fuera del lote |
| 2 | **§6.5 Serie 800** | Marcaste `[X] déjalo`, y en esas opciones `adelante` era *mi* propuesta de paraguas — así que «déjalo» significa «no hagas eso». «Déjalo como Serie-800» admite dos lecturas: déjalo **quieto**, o déjalo **como producto llamado así**. Y la huella pide prudencia: dispara en 14 documentos, 11 con dueño ya |
| 3 | **§6.4 `RHistorico.exe`** | Diste OK, pero s334 lo había dejado fuera A PROPÓSITO por riesgo léxico («R10 se cumple, la **grafía** no»), y mi propuesta reintroducía esa grafía como alias indexado. Merece tu re-adjudicación explícita, no colarse dentro de un «renombrar» |
| 4 | **suelo F5000** (2 manuales) | Dices «el modelo F5000 de **Morley**». El catálogo ya lo tiene como **`ffe:f5000`** consumible — adjudicado por **ti** en s91. FFE fabrica la barrera y Morley la revende. **Propongo** dejar `ffe:f5000` y añadir Morley a `vendido_bajo` (R3), sin duplicar el canónico. ¿OK? |
| 5 | **suelo MAD-490/492** | Escribiste «**parece** MAD-490 y MAD-492». Es conjetura, no firma — y el manual vivo de la web se titula sólo MAD-490. No creo dos productos sobre un «parece» |
| 6 | **suelo `MADT190_10`** (racks Notifier) | Los 9 canónicos que diste son **sólo dígitos** (`020-596`…) y el detector los excluye a propósito. Crearlos no los haría alcanzables. ¿Tienen nombre comercial, o aceptamos que sólo se lleguen por el nombre del rack? |
| 7 | **suelo `D 1100-4`** (KAC) | `CWSO-xx-S1/S2/W1/W2` donde «xx» es el color: es un patrón, no un modelo instanciable. ¿Qué colores existen de verdad? |
| 8 | **suelo `FS2-1`** | «La familia **FS** de Notifier, centrales de 1, 2 y 4 zonas». ¿El id es la familia, o son tres modelos? |
| 9 | **suelo `MNDT021`** | Es la única fila del suelo que no anotaste |

Con 1–3 resueltos entran 3 manuales más; con 4–9, otros 6. El resto del lote no depende de ellos.

### Las 4 bajas de corpus que firmaste: comprobadas antes de borrar

`scripts/s339h_precheck_bajas.py` mide qué se lleva por delante cada baja **antes** de ejecutarla.
**Ninguna toca un gold** y ninguna deja un producto consumible sin fuente. Resultado:

| manual | tu frase | qué cuesta |
|---|---|---|
| `MNDT740P` (2 chunks, portugués) | «es portugués, deberíamos sacarlo» | **nada**: `notifier:nas` conserva otras fuentes |
| `MNDT741I` (17 chunks, `language=en`) | «si sólo cambia el idioma, quitaría el de MNDT741I» | **nada**: la condición está verificada — `MNDT741.pdf` es `language=es`, mismo producto y mismo índice |
| `S3466R_Eng_ital` (1 chunk) | «retira este manual del corpus» | `unresolved:3466` se queda **sin ninguna fuente** |
| `Indicator Honeywell Manual SP` (1 chunk) | «Elimínalo del corpus» | `unresolved:indicator` se queda **sin ninguna fuente** |

👉 **Lo que sale de ahí y no me invento**: los dos últimos dejan un `unresolved:` en cuarentena
apuntando a nada. Lo coherente es **retirarlos** (`estado: retirado`, que es el mecanismo del
contrato), no dejar filas colgando. Lo aplico con las bajas si me dices que sí.

> Y un aviso de por qué esto se comprueba: mi primera lista tenía el **fichero equivocado** para
> «Elimínalo del corpus» — apuntaba a `MIEMA130`, que es el manual de la **VSN Plus** que el lote
> justamente promueve. Lo cazó este precheck, no yo.

---

## 🟠 Una decisión de despliegue: la categoría del Explorador no se mantiene sola

Preguntaste por qué salía «(sin clasificar)» en todo. **No era el panel.** La categoría y las
marcas de cada pregunta las escribe un barrido batch que **nunca ha corrido en producción**:
`requirements.txt` pide `python-telegram-bot` **sin el extra `[job-queue]`**, así que el worker
no tiene con qué programarlo y degrada a un warning en el log. El flag `CLASIFICADOR_PREGUNTAS`
además está en `off` por defecto.

La frontera es exacta: todo hasta el **18-ago 21:43** tenía categoría; todo desde el **20-ago
09:05** no. Las 109 que sí la tenían venían del **backfill manual**, no del barrido.

**Lo he arreglado para hoy** (22 filas clasificadas, $0,03, el Explorador vuelve a enseñar
categoría y marcas en las 131). Pero es un parche: la próxima pregunta vuelve a entrar sin
clasificar.

**Lo que necesito de ti**: el arreglo de raíz son dos cosas —`python-telegram-bot[job-queue]` en
`requirements.txt` y `CLASIFICADOR_PREGUNTAS=on` en Railway— y **no lo he hecho porque cambia la
imagen de producción y enciende también otro job dormido**: el refresco de presencia del catálogo
(cada 720 s), que hoy no corre y cuya conducta al despertarse nadie ha medido. Dime si tiro y lo
mido, o si prefieres seguir con el backfill a mano. Está en `TECH_DEBT #100` con el detalle.

---

## ⚪️ Y lo que ya no te espera

- **La Wiki de modelos está construida**, como pediste, en `/catalogo` del panel. 1.024 modelos,
  36 marcas, con sus manuales, sus alias y las dos preguntas que el markdown nunca podía contestar:
  **55 modelos sin ningún manual** y los manuales huérfanos, que empezaron en **245** y hoy van por
  **82** (de los cuales **53 esperan una decisión tuya**, no una herramienta).
- **Las reglas nuevas están escritas y son legibles por el generador**:
  `data/catalog/reglas_clasificacion.json`, R9–R18, cada una anclada en la anotación tuya que la hizo
  nacer. La más cara de tu pasada fue R10 («aunque sea software, los técnicos también deberían poder
  preguntar sobre ello»): **18 de tus 57 anotaciones** eran esa misma frase.
- **La propuesta de automatización** está en `evals/s331_automatizacion_propuesta_v1.md`, y empieza
  reconociendo que **la medida mató mi primera idea**. Iba a proponer auto-aplicar los patrones que
  ya habías firmado; los números dicen que P1 acierta **60%** y P3 **44%** sobre esta población, así
  que auto-aplicarlos habría escrito 11 decisiones equivocadas. Lo que sí sale de la medida: el
  **40%** de tu esfuerzo fueron filas **duplicadas** (`morley:tg` te lo pregunté **15 veces**), y eso
  no lo arregla ningún modelo mejor — lo arregla agrupar por id.
- **Tu otra pregunta** (¿el ZLSM_MD está repetido en español?): **no son duplicados**. El español es
  la **ficha** (`DS_KIDDE_ZLSM_MD…ES`) y el inglés el **manual de instalación**
  (`MI_KIDDE_ZLSM_MD…ING`). Distinto tipo de documento, los dos se quedan. Mismo patrón en ZLSM_ME y
  ZLSM_MR.
