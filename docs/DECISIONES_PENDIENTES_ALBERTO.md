# Lo que espera tu decisión — cierre de s331 (21-ago-2026)

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

## 🟡 Manuales huérfanos: lo que sí pude cerrar solo, y lo que necesita tu firma

Pediste atacar los manuales sin modelo de forma autónoma. **Hecho: 245 → 193.** 81 productos
salieron de la cuarentena (601 → 520) y **52 manuales** dejaron de ser inalcanzables por nombre
de modelo. Todo con cita verificada en su propio documento, dry-run del gate en PASS y el efecto
comprobado uno a uno con el resolver real. El resto **no lo toco porque no es mecánica, es
adjudicación tuya**, y son tres preguntas concretas.

### 1. Rebrands Morley ↔ Notifier ↔ Sensitron (10 ids, 5 tokens)

Cinco tokens existen en **dos marcas a la vez** y su fila de homónimos está abierta
(`candidate: true`, `fail-open`), así que el resolver se planta y el manual no llega. Promover el
producto no arregla nada mientras el homónimo siga abierto. **¿Son el mismo producto rebrandeado,
o dos productos distintos?**

| token | ids | tu decisión |
|---|---|---|
| `MCX-55M` | `morley:mcx-55m` · `notifier:mcx-55m` | ¿mismo producto? |
| `MMX-10M` | `morley:mmx-10m` · `notifier:mmx-10m` | ¿mismo producto? |
| `NFS8REL` | `morley:nfs8rel` · `notifier:nfs8rel` | ¿mismo producto? |
| `SP-200` | `morley:sp-200` · `notifier:sp-200` | ¿mismo producto? |
| `PL4` | `notifier:pl4` · `sensitron:pl4` | ¿mismo producto? |

Morley es marca del grupo (Honeywell), así que **mi apuesta es que los cuatro primeros son el
mismo módulo con dos etiquetas** — pero R8 dice que la grafía la manda el fabricante y esto es
exactamente el caso `D838-1_kac sounders` que ya nos mordió una vez. No lo decido yo.

### 2. Gemelos: dos ids para un mismo token (4 ids)

| candidate | ya resuelve a | qué pasa |
|---|---|---|
| `notifier:id-3000` («ID-3000») | `notifier:id3000` («ID3000») | misma marca, **grafía distinta**: ¿cuál es la canónica? |
| `notifier:st.pl4+` («ST.PL4+») | `notifier:stpl4` («STPL4») | el gemelo **también** está en cuarentena |
| `notifier:tg-1020` («TG-1020») | **`desico:tg-1020`** | **otra marca**: ¿colisión o rebrand? |
| `sensitron:pl4+` («PL4+») | homónimo `PL4` abierto | depende de (1) |

### 3. Los 8 que el dúo me hizo retirar del lote

Pasaban mi filtro y aun así salieron. Los tres primeros porque **no son productos**; los cinco
siguientes porque promoverlos **quitaba fuentes** a las consultas de esos mismos productos:

- `notifier:eia-485` — **EIA-485 es el bus RS-485**, no un producto. Sus 71 menciones son el
  manual explicando el cableado. Promoverlo habría secuestrado toda consulta de bus. → **retirar**.
- `notifier:ad-pe` — «Versión Exd (AD-PE)» es un sufijo de variante (1 mención, en una tabla de
  versiones). El producto real, `notifier:smart-2-exd-ad-pe`, sí entró.
- `notifier:rhistorico.exe` — el software **sí** es producto (tu R10), pero se llama «Reparación
  de Históricos»; `RHistorico.exe` es su ejecutable. → **renombrar el canónico**.
- `notifier:tg-6000`, `notifier:tg-6000-net`, `notifier:tg-notifier` — al promoverlos, la consulta
  pierde el paraguas `TG` y con él **los 4 manuales genéricos del TG** (Introducción, Usuario,
  Técnico, requisitos del PC), que son justo los que responden. → hace falta una **relación de
  catálogo** que ate los TG-xxxx a esos genéricos, no una promoción.
- `systemsensor:8100e-faast` — igual, pero peor: 14 fuentes → 1. Y toca la atribución
  **FAAST/Xtralis** que ya tienes pendiente más arriba.

### 4. Lo que queda huérfano y por qué (193)

- **181** son `unresolved:` — sin marca. Asignar fabricante es adjudicación, no mecánica.
- **53** no tienen ningún candidate: sus ids están retirados o son redirect. Es otro problema.
- **15** no tienen cita limpia en su propio documento; **7** son acrónimos cortos (`VIEW` sale
  1.648 veces en el corpus por ser una palabra inglesa).
- **5** el detector no puede ni verlos: `00051`, `03382`… son referencias puramente numéricas y
  `EEV(2)` lleva paréntesis.

### 5. Una que te menciono sin bloquear nada

Cuatro productos que entraron llevan namespace `notifier:` y son **Sensitron** en la portada
(`SMART 3 CC-CD`, `SMART 3 CD`, `SMART3G-D`, `SMART3G`). Los manuales son de Notifier España
(MN-DT-62x) y el técnico pregunta por el modelo, no por el namespace, así que los dejé dentro
para no tener 3 manuales huérfanos por una cuestión de contabilidad. Si prefieres moverlos a
`sensitron:`, es un redirect y es barato.

---

## ⚪️ Y lo que ya no te espera

- **La Wiki de modelos está construida**, como pediste, en `/catalogo` del panel. 1.024 modelos,
  36 marcas, con sus manuales, sus alias y las dos preguntas que el markdown nunca podía contestar:
  **55 modelos sin ningún manual** y **245 manuales huérfanos** (184 de ellos, sólo porque todos sus
  ids siguen en cuarentena — adjudicarlos los desbloquea).
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
