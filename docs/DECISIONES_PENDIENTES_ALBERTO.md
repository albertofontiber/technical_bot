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

## 🔴 Manuales huérfanos: 245 → 82, y **5 líneas tuyas los bajan a 65**

Me dijiste que atacara hasta 10. Bajé de **245 a 82** y ahí me paré, pero esta vez no me paré por
prudencia: **medí por qué**, y el resultado es que el cuello de botella dejó de ser técnico.

### Lo primero: 5 decisiones que valen 17 manuales

Son redirects de un `unresolved:X` a su gemelo **que YA es consumible** — mismo canónico, uno con
la marca puesta y otro sin ella. **R21 dice que esto lo firmas tú**, y por eso no lo he tocado.

| firma esto | manuales que desbloquea |
|---|---|
| `unresolved:id50` → `notifier:id-50` | **12** (`MADT155_*`, `MCDT155/156`, `MFDT155/156`, `MIDT155/156`, `TIDT107`, `BIDT077`) |
| `unresolved:tg` → `notifier:tg` | 2 |
| `unresolved:id60` → `notifier:id-60` | 1 |
| `unresolved:tg-gsm` → `notifier:tg-gsm` | 1 |
| `unresolved:mad-450` → `detnov:mad-450` | 1 |

**Simulado sobre una copia del catálogo, no razonado: 82 → 65, y 0 huérfanos nuevos.**
👉 *Un «ok a las 5» y lo aplico con gate y recibo.*

### Cuatro que no puedo proponerte porque el gemelo existe en DOS marcas

| documento | el token lo ocupan |
|---|---|
| `HLSI-MN-025-I_NFS Supra Series v05` | `morley:vsn12-2plus` **y** `notifier:vsn12-2plus` |
| `VSN-CO-Mantenimiento-y-vida-util…` | `morley:vsn-co` **y** `notifier:vsn-co` |
| `TG-1020-INT` | `desico:tg-1020` **y** `unresolved:tg-1020` (y el candidate de Notifier) |
| `TG-Honeywell_Usuario_PT` | `notifier:id3000` ya es consumible; `notifier:id-3000` es su gemelo con guion |

Los dos últimos los cazó el gate y el dúo cuando intenté promoverlos: no son promociones, son
gemelos ortográficos. Y siguen las **3 fusiones Morley↔Notifier** de siempre (`NFS8REL`,
`MCX-55M`, `MMX-10M`), cada una con manual huérfano en los dos lados → **6 más de golpe**.

### Y una pregunta de regla que vale 15 manuales

Los manuales Detnov **no usan el nombre de modelo: usan el número de referencia**. `MAD-491` es
`55349102`, `MAD-461` es `55346102`. Lo verifiqué leyendo el PDF original: la referencia está en
el texto, **ya es alias en el catálogo**, y coincide con el nombre del fichero (doble ancla).

👉 **¿Vale el nº de referencia del fabricante como cita válida bajo R4 cuando el manual no usa el
nombre de modelo?** Si vale, son **15** de golpe. Si no, se quedan.

### El suelo, y por qué 10 no sale sin ti

Medí los 82 leyendo **el PDF original de cada uno** (`s336b`/`s336c`, los 84 de entonces):

| | n | qué lo desbloquea |
|---:|---|---|
| redirect `unresolved:` pendiente | 29 | **tú** (los 17 de arriba + los ambiguos) |
| promovible con cita verificada | 20 | mío — **hechos los que pasan R19/R21: 2** |
| sólo nº de referencia | 15 | **tú**, la pregunta de arriba |
| el manual no nombra su producto | 13 | nada: no lo atesta |
| canónico digit-only | 4 | irreducible, el detector los excluye a propósito |
| PDF escaneado | 2 | lector multimodal |
| sin PDF | 1 | — |

**53 de los 82 están gated en decisiones tuyas.** No hay camino autónomo a 10 sin saltarme R21,
que es exactamente lo que el dúo me cazó intentando en r43.

### Lo que sí hice solo, y lo que me costó

De los 20 «promovibles», **R19 y R21 se comieron 17**. Y el que mejor pinta tenía, `AM-LCD`, lo
mató la medida que hice para defenderlo: Fable señaló que el censo del gate lo flagea
`[sin_digitos, acronimo_corto]` —la clase con la que la regla mata `NAS`—, medí su huella en el
corpus esperando limpiarlo, y **uno de sus 6 documentos es un falso positivo real**: «Pantalla
**FM/AM LCD**» de un manual de radio. Quedaron **2**: `SDX-751-TEM` y `LPX-751`.

Eso deja una pregunta abierta que no es de este lote y que arreglaría `AM-LCD` de raíz:
**¿debe un término sin dígitos exigir el separador en el detector?** (hoy `am[-\s/.+]*lcd` acepta
el espacio, y por eso «FM/AM LCD» cuela). Tiene que ir con su propia medida.

**Y hay 5 que no bajan de ninguna manera**: `020-590`, `55320103`, `3466`, `00051`, `EEV(2)` —
referencias puramente numéricas o con paréntesis, que el detector excluye **a propósito**. De
`3466` te traigo un dato nuevo: leí su PDF escaneado con Claude y **la página sí imprime «3466»**,
así que la cita existe; lo que no existe es un nombre de producto que el detector pueda ver.

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
