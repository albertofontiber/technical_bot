# s331 — Automatizar la asignación de manuales · **v2, POST-DÚO r40**

**SUPERSEDE a `evals/s331_automatizacion_propuesta_v1.md`** (la versión que atacó el dúo).

**Encargo de Alberto (21-ago)**: «me gustaría que "aprendieses" de la clasificación […] creo que será
importante **automatizar este proceso de asignación de manuales para minimizar el trabajo manual,
aunque siempre haya alguien que lo valide**, […] para mejorar a medida que añadimos más fabricantes y
manuales».

**Dúo r40**: Sol xhigh (60 tool-calls sobre el repo) — **2 críticos + 4 medios, los 6 confirmados
contra el código, 0 falsos positivos**. Fable — **3 medios + 3 menores, los 6 confirmados, veredicto
«No SÓLIDO»** (la review quedó SIN emparejar: entre las dos corridas edité otros ficheros del repo y
el manifiesto contra HEAD dejó de coincidir; el contenido es válido, la traza de emparejamiento no).
**Doce hallazgos cambiaron la propuesta antes de que llegara a ti**, y dos destaparon que yo había
citado evidencia falsa y que mi propia herramienta se contradecía a sí misma.

**Estado**: NADA cableado. Esto es el rumbo, con la medida delante.

---

## 0. Lo que el dúo cambió — primero, porque incluye un error mío

### C1 · La evidencia del K=5 estaba mal leída *(Sol, crítico, confirmado)*

La v1 decía: «el re-juicio K=5 cross-model de `spectrex:40-40l` **convergió 5/5** en el veredicto
equivocado». **Es falso.** `evals/s324c_rejuicio_k5_v1.md:81` dice:

```
- E1 `spectrex:40-40l`(40-40L): S5 ART×3, G PROD×2, v5/5
```

El `v5/5` son los **votos VÁLIDOS** (5 de 5 emitidos fueron parseables), no la convergencia. El panel
se **partió 3-2**: Sonnet-5 dijo ARTEFACTO ×3, GPT dijo PRODUCTO ×2. El propio packet lo imprime
al lado de la fila: «re-juicio K=5 **NO convergente**». Yo lo confundí con las filas que sí
convergieron ({'ARTEFACTO_EXTRACCION': 5}).

**Qué sobrevive y qué no.** No sobrevive «más modelo no sirve»: con un panel partido 3-2 **no puedo
descartar que un juez mejor ayude**. Lo que sí muestra el caso, y con más fuerza que lo que yo
afirmaba, es que **ninguno de los dos bandos podía acertar**: la respuesta correcta —«son cuatro
modelos, enumerados en la §1.1 de la p.9»— **no era expresable en una rúbrica producto-vs-artefacto**.
Lo vinculante es **la pregunta**, no el modelo. Ese es el argumento de la descomposición, y ahora
descansa en algo verificable.

### C2 · «Mismo id = misma decisión» es falso *(Sol, crítico, confirmado)*

La v1 vendía el 40% de duplicados como «trabajo eliminable, riesgo cero, agrupando por id». Medido
fila a fila, **3 de los 9 ids repetidos llevan decisiones DISTINTAS por documento**, y agrupar por id
a secas **las perdería**:

| id | documento A | documento B | ¿misma decisión? |
|---|---|---|---|
| `notifier:nfs-32-001` | `D1056` → **NFXI-BS / NFXI-BSF** | `D838` → **gama WMSOU** | **NO** |
| `xtralis:vesda` | `HSLI_IN_020` → re-atestar al **software TG** | `Cursos formacion` → **BAJA del corpus** | **NO** |
| `notifier:airsense` | `MADT731_04` → **HSSD-2** | `TIDT109` → **software Classifire** | **NO** |
| `kidde:ke-dba-sktw` | «OK con juez» | «…y es accesorio de KE-DB3010W» | complementarias |
| `kidde:zlsm-md` | «…también `9-30501-KID`» | «¿está repetido en ESP?» | complementarias |
| `morley:tg` ×15 | la misma frase, 15 documentos | | **SÍ** |
| `notifier:faast-lt`, `kidde:2a-pak-hpl`, `kidde:zlsm-mr` | | | **SÍ** |

**Reparto corregido de las 23 duplicadas**: **17 eliminables sin riesgo** (14 de ellas `morley:tg`) ·
**2 que exigen preservar la unión** de las dos notas · **3 que NO se pueden agrupar**.

**Consecuencia de diseño**: la clave de agrupación es **(id × operación)**, no el id. El packet
agrupa por id para PRESENTAR —una entrada, con sus N documentos listados— y obliga a una nota por
documento **sólo cuando la operación difiere**. Sigue siendo el ahorro más grande y ya no es «riesgo
cero»: es «riesgo acotado por una clave correcta».

### M1 · Q2/Q3/Q5 no son deterministas en su veredicto *(Sol, medio, confirmado)*

`docs/RULER_DESIGN.md:144-151` ya lo dice: el grep es fiable **por página**, y quien decide es el
render. Que un documento no tenga encabezado «Descripción general» **no prueba** que no enumere
variantes, y decidir si un PDF comercial tiene detalle técnico exige leerlo, no buscarlo.

**Corrección**: los tres detectores son **deterministas en su DISPARO, no en su VEREDICTO**. Cuando
disparan, obligan a citar; cuando no disparan, **no dicen nada** — y ese silencio es su modo de
fallo. La v1 decía «enriquecer no puede escribir nada mal»: **falso**, un «no enumera modelos»
equivocado sesga al humano hacia el sí. Por eso la salida del detector se redacta como
**«no encontrado por regla, sin comprobar»** y nunca como «no hay».

### M2 · El 93% de Q1 no era reproducible *(Sol, medio, confirmado)*

El censo sólo calcula el P1 monolítico (9/15). El «14/15» era una descomposición **a mano** que no
está en ninguna herramienta. Recontado con el criterio estricto, sobre las 15 filas P1:

| | |
|---|---|
| grafía aceptada limpia | **9** |
| aceptada pero **incompleta** (`zlsm-md`, `repetidor-serie-1000`, `40-40l`) | 3 |
| grafía **corregida** por Alberto (`40-40-air`: `777650` → `TM777650`) | 1 |
| **equivocada** (`nfs-32-001`: era una norma) | 1 |
| no adjudica grafía (`fl-20`: sólo ordena retirar el doc) | 1 |

**9/14 aplicables (64%) estrictamente; 12/14 (86%) si «no contradicha» cuenta.** Ninguno de los dos
es 93%, ninguno tiene gold independiente y n=15. **Q1 no autoriza auto-aplicación hoy.**

### M3 · Una muestra de 5 no valida un bloque *(Sol, medio, confirmado)*

Con una tasa del 93%, una muestra de 5 tiene **0,93⁵ ≈ 70%** de probabilidad de **no ver ni un
error**. Y CAS/backup revierte lo detectado, no lo omitido. **Corrección**: la auditoría se dimensiona
al riesgo (para ver un error del 7% con 95% de confianza hacen falta ~41 filas), o directamente se
revisa la lista entera con el diff visible — que para 15 filas es más barato que la estadística.

### M4 · Los 69 documentos son una población seleccionada por fallar *(Sol, medio, confirmado)*

Medir los detectores sobre los 69 documentos que quedaron sin `doc_map` mide el residuo, no la
generalización: son justo los que el proceso anterior no supo resolver. **Corrección**: la cohorte de
medida es **69 residuo + una muestra aleatoria de los 983 ya mapeados** (control limpio: los
detectores deben acertar donde ya sabemos la respuesta) + **los documentos que entren nuevos**, que
son la población que de verdad importa.

### M5 · Dependencias no inspeccionadas *(Sol, declarado)*

Sol agotó el cap de tool-calls sin verificar: el censo vivo de Supabase (1.052/69), los PDFs y su
render, las webs OEM y el JSON crudo de votos K=5. Queda declarado: **esas cifras las he medido yo y
no están verificadas por un tercero**.

### F1 · Mi propia herramienta usaba DOS definiciones de «acuerdo» *(Fable, medio, confirmado)*

`s331_censo_anotaciones.py` medía con dos varas en sus dos mitades: `censar` exigía que la nota fuese
**sólo** un asentimiento, y `acierto_de_patrones` sólo que **empezara** por uno. Consecuencia: «OK con
juez. este doc va sobre la familia FAAST LT» salía **a la vez** como «corrección» y como acierto — y
el numerador que justifica escribir reglas nuevas quedaba inflado **en la dirección que favorecía mi
propuesta**.

Reconciliado a **una escala de tres**, y el reparto cambia:

| clase | anotaciones | ids distintos |
|---|---|---|
| confirmación **pura** | 14 | 12 |
| confirmación **con matiz** (empieza por OK y añade algo) | **7** | **4** |
| **corrección** (hubo error de verdad) | 36 | **18** |

Las «22 correcciones» de la v1 eran **18**. Y la clase intermedia no es un artefacto contable: es
**donde nace una regla sin que se haya tomado ninguna decisión equivocada**. R13 y R17 salen casi
enteras de ahí, y ahora lo declaran en el fichero de reglas.

### F2 · El gap #6 de la v1 daba un ejemplo falso *(Fable, menor, confirmado)*

La v1 decía que el censo «cuenta como acuerdo cualquier nota que empiece por OK, y Alberto escribió
"casi OK con juez"». **Falso**: `_EMPIEZA_OK` exige empezar por `ok|vale|correcto|de acuerdo`, y «casi
OK» empieza por «casi» — esa fila sale marcada como fallo en P1 y en P3. El sesgo declarado existía;
el ejemplo con que lo ilustraba, no.

### F3 · «Medir sobre 69 es barato» omite el coste del ground truth *(Fable, menor, confirmado)*

Precisión y recall exigen **verdad de referencia**, es decir adjudicar a mano una cohorte. Eso es
trabajo humano **no presupuestado** — justo el denominador que el gap declara no tener. Medir los
detectores no es gratis: cuesta exactamente lo que se quiere ahorrar, una vez.

### F4 · «El caso D838 es la prueba de que funciona» sobre-afirma *(Fable, menor, confirmado)*

La verificación de especificaciones es real, pero **la decisión sobre WMSOU está pendiente de
Alberto**, y hay una discrepancia que la v1 omitía: el documento es **`D838 issue 1`** mientras la
hoja publicada de WMSOU es **`D800 issue 8`**. El hardware coincide; el número de documento es de otra
tirada, probablemente una edición de cliente. Va declarado aquí y no sólo en el documento de
decisiones.

---

## 1. Las cifras

**El corpus y el catálogo** (`dashboard/catalogo.py`; censo contra Supabase vivo):

| | |
|---|---|
| documentos activos | 1.052 |
| …con fila de `doc_map` | **983 (93%)** |
| …**sin** fila de `doc_map` | **69 (6%)** |
| modelos que el bot consume | 1.024, en 36 marcas |
| …sin ningún manual | 55 |
| candidates en cuarentena | 601 |
| documentos huérfanos | 245 |
| …huérfanos SÓLO porque todos sus ids son candidate | **184** |

**La pasada de Alberto** (`scripts/s331_censo_anotaciones.py`):

| | |
|---|---|
| anotaciones escritas | 57 |
| decisiones **distintas** | 34 |
| duplicadas | 23 — de ellas **17 eliminables**, 2 a unir, **3 no agrupables** |
| distintas que son puro «OK» | 12 |
| distintas que son «OK» **+ matiz** | 4 |
| distintas que son **corrección** | **18** |

**El acierto de lo que el packet le recomendaba** — la cifra que decide qué se automatiza:

| patrón | acierto | lo que el v3 le decía |
|---|---|---|
| **P4** | **7/7 (100%)**, n=7 | «tuya» |
| **P1** | **9/15 (60%)** | «es el patrón que firmaste **9 veces**» |
| **P3** | **4/9 (44%)** | «sin menciones, no es un producto» |
| total | **20/32 (62%)** | |

El «9 veces» era cierto en §1.B del **v2** y se presentó como confianza sobre las filas del **v3**:
una **tasa base heredada de otra población**. Es la clase de error que el gate impide abajo, cometida
arriba, donde no hay gate. Queda como guarda: *el umbral se mide sobre la población que se va a
aplicar, cada ronda*.

---

## 2. El diagnóstico: incompletitud, no error

Descompuestos los 6 fallos de P1: **1 equivocada · 1 con la grafía corregida · 3 incompletas ·
1 sobre otra pregunta**. En 4 de 6, lo que el juez proponía no era falso — era parcial.

La causa es estructural y está a la vista: **cada fila pregunta UNA cosa** («¿existe este
candidate?», «¿cuál es su grafía?») cuando el documento plantea **seis independientes**. Un veredicto
único no puede ser correcto porque no puede ser completo. Y el caso `spectrex:40-40l` lo demuestra sin
apelar a ningún modelo: dos familias de jueces se repartieron 3-2 sobre una rúbrica en la que **la
respuesta correcta no cabía**.

---

## 3. RECOMENDACIÓN — descomponer en seis preguntas con umbral propio

| # | pregunta | regla | quién la contesta | acierto medido |
|---|---|---|---|---|
| **Q1** | ¿cuál es la grafía canónica? | R8 | juez | 9/14 estricto · 12/14 laxo, n=15, **sin gold** |
| **Q2** | ¿es un producto, o es otra cosa? (norma · fabricante · código · **software**) | R10, R14 | detector (dispara) + juez (decide) | sin medir |
| **Q3** | ¿cuántos modelos hay? ¿el cuerpo enumera variantes? | R9 | detector (dispara) + lectura dirigida | sin medir |
| **Q4** | ¿de quién cuelga? (accesorio · familia · sistema) | R13, R15, R16, R17 | juez con el catálogo delante | sin medir |
| **Q5** | ¿debe este documento estar en el corpus? | R11 | detector (dispara) + render | sin medir |
| **Q6** | ¿hay más identificadores en la portada? | R12 | extractor de portada | sin medir |

Los detectores de Q2/Q3/Q5 **disparan** de forma determinista y **no concluyen**: cuando encuentran
—«hay una sección "Descripción general" en la p.9», «este token casa con `NF S`»— obligan a citarla;
cuando no encuentran, emiten **«no encontrado por regla, sin comprobar»**, nunca «no hay».

Aun con esa cautela, cubren **4 de los 6 fallos de P1** y **4 de los 5 de P3**.

**Por qué es BP, estructural y escalable:**

- **BP**: cada sub-pregunta tiene acierto medible por separado, así que la auto-aplicación se calibra
  donde hay evidencia y se queda quieta donde no la hay. Un veredicto monolítico no se puede
  calibrar: no se sabe qué parte falló. Hoy **ninguna** tiene evidencia suficiente, y eso también es
  un resultado.
- **Estructural**: ataca la raíz medida —la rúbrica no admite la respuesta correcta— y no el síntoma.
- **Escalable a 30+ fabricantes**: los detectores son reglas sobre la FORMA de un documento técnico,
  no sobre una marca. Sólo Q4 crece con el fabricante, y crece contra el catálogo, que ya escala.

### El orden, por relación valor/riesgo

**Nivel 0 — agrupar por (id × operación). Hoy.**
Se lleva **17 de las 57 anotaciones** sin tocar ningún clasificador. `morley:tg` se le preguntó **15
veces**. La clave lleva la operación dentro precisamente porque 3 ids repetidos NO son la misma
decisión (C2).

**Nivel 1 — los tres detectores, primero MEDIDOS.**
Cohorte: 69 residuo **+ muestra aleatoria de los 983 ya mapeados** (control limpio) **+ los nuevos**.
Métrica: precisión, recall **y falsos «no hay»**, que es su modo de fallo peligroso. Sólo después se
enchufan, y como enriquecimiento de la fila, no como veredicto.
**Coste declarado** (Fable F3): esto NO es gratis — precisión y recall exigen verdad de referencia, o
sea adjudicar la cohorte a mano. Cuesta una vez lo que se quiere ahorrar siempre, y ese presupuesto
hay que pedírselo a Alberto antes de empezar, no después.

**Nivel 2 — auto-aplicación: HOY NINGUNA.**
Q1 era la candidata y su número real (9/14 estricto, sin gold, n=15) no lo autoriza. Lo que se hace
antes es construirle un gold: adjudicar la grafía de una muestra contra la ficha del fabricante, y
medir el juez contra eso. Cuando haya número, la auditoría se dimensiona al riesgo — no cinco filas.

**Nivel 3 — validación contra la web del fabricante (R18), acotada.**
Es lo que Alberto hizo a mano 4 veces en su pasada y lo que resolvió los 3 casos más difíciles de la
sesión. No es «navegar»: es buscar la ficha del token y **comparar N especificaciones**. El caso
`D838` muestra que **discrimina**: las ocho especificaciones del documento coinciden literalmente con
la hoja de WMSOU (System Sensor) y **no** con las de sus hermanos rebrandeados (KAC `WSO-`, Notifier
Opal `NFX-WS-`: 95 dB(A) e IP21C/IP44 frente a 100 dB(A) e IP24/IP65). Un juez leyendo sólo el PDF no
podía llegar ahí.
**Pero no es «la prueba de que funciona»** (Fable F4): la decisión sobre WMSOU sigue **pendiente de
Alberto**, y queda una discrepancia sin explicar — el documento es `D838 issue 1` y la hoja publicada
es `D800 issue 8`. Es **una** validación exitosa, con n=1 y un cabo suelto.

**El humano no desaparece en ningún nivel** — requisito explícito de Alberto, y DEC-261 demostró por
qué: una nota suya mal ubicada produjo 6 atestaciones equivocadas. Lo que cambia es **qué se le
pide**: hoy adjudica fila a fila; después decide sólo lo que ningún detector puede decidir.

---

## 4. Alternativas descartadas

1. **Un juez mejor.** **YA NO SE DESCARTA** (Sol C1). Con el panel partido 3-2 no hay evidencia para
   descartarlo. Lo que sí está establecido es que un juez mejor **sobre la misma rúbrica** no puede
   llegar a «son cuatro modelos»: la respuesta no cabe en producto-vs-artefacto. Primero la pregunta,
   después, si hace falta, el modelo.
2. **Afinar un modelo con sus anotaciones.** 34 decisiones no son un conjunto de entrenamiento, son
   un conjunto de reglas —y como reglas ya están escritas y son legibles—; y un afinado no se audita
   fila a fila, que es lo que el gate exige.
3. **Auto-aplicar los patrones firmados.** Era mi propuesta inicial. La mata su propia medida:
   P1 60%, P3 44%.
4. **Automatizar sin humano.** Contra el encargo explícito y contra DEC-261.
5. **Un CMS aparte para los modelos.** Descartada al construir la Wiki: el catálogo gobernado ya es
   esa base y es lo que el bot consulta. Por eso `/catalogo` es una VISTA de sólo lectura.
6. **Atacar primero los 601 candidates.** Por orden: **184 de los 245 documentos huérfanos** se
   desbloquean solos al adjudicar candidates, y medir sobre 69+control es barato; sobre 601, no.

---

## 5. Gaps y riesgos declarados

1. **Ninguna sub-pregunta tiene hoy acierto suficiente para auto-aplicarse**, Q1 incluida. Todo el
   Nivel 1 y 2 es «propongo medir».
2. **n=15, n=9, n=7** y sin gold independiente. P4 al 100% con n=7 no autoriza nada.
3. **El modo de fallo peligroso de los detectores es el silencio** (un «no encontrado» que sesga al
   humano hacia el sí), y no está medido.
4. **R13 no se puede cablear**: `relations.jsonl` no tiene `accessory-of`. Bloquea dos filas ya
   adjudicadas y necesita el sí de Alberto.
5. **`TECH_DEBT #97` sigue abierto**: `product_model` y `manufacturer` no son persistentes. Los
   detectores propuestos leen el CONTENIDO, no la etiqueta, precisamente por esto.
6. **No he medido el coste marginal de un documento nuevo**, que es la magnitud que importa para «a
   medida que añadimos fabricantes». Sé el backlog (69), no el coste del documento 1.053. Sin ese
   número, «minimizar el trabajo manual» no tiene denominador.
7. **La escala de «acuerdo» sigue siendo tosca**, aunque ya es coherente: distingue tres clases por
   la FORMA de la nota, no por su contenido. Un «OK» que en realidad esconde una reserva se cuenta
   como acuerdo. La dirección del sesgo favorece al sistema, así que la tasa real es igual o peor que
   la medida, nunca mejor. *(La v1 ilustraba esto con «casi OK con juez» y el ejemplo era falso —
   Fable F2: esa fila sí sale marcada como fallo.)*
8. **Seis preguntas por documento es más superficie que hoy.** Si cada una llama a un modelo, el coste
   por documento se multiplica. Mitigación propuesta —tres deterministas gratis y las otras tres en
   una sola llamada estructurada— **también sin medir**.
9. **Sin verificación de tercero** sobre el censo de Supabase, los PDFs, las webs OEM y el JSON crudo
   de votos K=5: Sol agotó el cap de tool-calls antes de llegar (M5).
