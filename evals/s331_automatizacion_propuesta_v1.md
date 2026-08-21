# s331 — Automatizar la asignación de manuales: propuesta para el dúo

**Encargo de Alberto (21-ago)**: «me gustaría que "aprendieses" de la clasificación que hemos ido
haciendo para que mejores tu clasificación a futuro […] creo que será importante **automatizar este
proceso de asignación de manuales para minimizar el trabajo manual, aunque siempre haya alguien que
lo valide**, […] para mejorar a medida que añadimos más fabricantes y manuales».

**Estado**: NADA cableado. Esto es el rumbo, con la medida delante, para que el dúo lo ataque antes
de construir nada.

---

## 0. Las cifras, primero

Todas medidas hoy, reproducibles con los scripts que se citan.

**El corpus y el catálogo** (`dashboard/catalogo.py`, `scripts/s331_censo_anotaciones.py`):

| | |
|---|---|
| documentos activos | 1.052 |
| …con fila de `doc_map` | **983 (93%)** |
| …**sin** fila de `doc_map` | **69 (6%)** |
| modelos que el bot consume | 1.024, en 36 marcas |
| …sin ningún manual | 55 |
| candidates en cuarentena | 601 |
| documentos huérfanos (no atestan a nadie consumible) | 245 |
| …de ellos, huérfanos SÓLO porque todos sus ids son candidate | **184** |

**La pasada de Alberto sobre el packet v3** (`evals/s331_censo_anotaciones_resultado_v1.txt`):

| | |
|---|---|
| anotaciones que escribió | 57 |
| decisiones **distintas** | 34 |
| anotaciones **duplicadas** | **23 (40%)** — `morley:tg` ×15 |
| de las distintas, puro «OK» | 12 (35%) |
| de las distintas, **corrección** | 22 |

**El acierto de lo que el packet le recomendaba** — la cifra que decide qué se puede automatizar:

| patrón | acierto en el v3 | lo que el v3 le dijo |
|---|---|---|
| **P4** (nombre real con barra) | **7/7 (100%)** | «tuya, comprueba la grafía» |
| **P1** (seguir al juez) | **9/15 (60%)** | «es el patrón que firmaste **9 veces**» |
| **P3** (retirar artefacto) | **4/9 (44%)** | «sin menciones, no es un producto» |
| P5 | 0/1 | n=1, sin señal |
| **total** | **20/32 (62%)** | |

---

## 1. La medida mata mi primera propuesta, y hay que decirlo

Iba a proponer **auto-aplicar los patrones que Alberto ya había firmado**, empezando por P1 y P3,
con auditoría por muestra. Los números lo prohíben: auto-aplicar P1 habría escrito **6 decisiones
equivocadas de 15**, y P3 **5 de 9**.

Y hay algo peor que el número: **el v3 le presentó P1 como «el patrón que firmaste 9 veces»**. Era
verdad — en §1.B del **v2**. Sobre la población del v3 es 60%. Es una **tasa base heredada de otra
población**, presentada como confianza. Es exactamente la clase de error que el gate existe para
impedir, cometido en la capa de arriba, donde no hay gate.

**Corolario para el diseño**: cualquier umbral de auto-aplicación se mide sobre la población que se
va a aplicar, cada ronda, o no vale. Va escrito como guarda, no como buena intención.

## 2. Pero el fallo no es el que parece: es INCOMPLETITUD, no error

Al descomponer los 6 fallos de P1 fila a fila, la propuesta del juez era correcta **en lo que
proponía** en 5 de los 6; lo que faltaba era todo lo demás del documento:

| fila | qué propuso el juez | qué dijo Alberto | veredicto |
|---|---|---|---|
| `kidde:zlsm-md` | grafía `MiniLaser` | «casi OK… pero la portada también trae `9-30501-KID`» | **incompleta** |
| `notifier:repetidor-serie-1000` | `Repetidor de la Serie 1000` | «también como *repetidor central ID1000*» | **incompleta** |
| `spectrex:40-40l` | `S40/40L` | «son CUATRO: L, LB, L4, L4B (§1.1 de la P9)» | **incompleta** |
| `spectrex:40-40-air` | `40/40 Air Shield (P/N 777650)`, padre «serie 40/40» | «accesorio de la familia 40/40; el P/N es `TM777650`» | **incompleta** |
| `morley:fl-20` | `FAAST LT (serie FL20)` | «es documentación en portugués, retíralo» | **ortogonal** |
| `notifier:nfs-32-001` | `NF S 32-001` | «es una NORMA» | **equivocada** |

**1 de 15 equivocada. 4 incompletas. 1 sobre otra pregunta.** El juez sabe deletrear; lo que no sabe
es cuándo ha terminado.

La causa es estructural y está a la vista: **cada fila pregunta UNA cosa** («¿existe este
candidate?», «¿cuál es su grafía?») cuando el documento plantea **seis independientes**. Un veredicto
único por fila no puede ser correcto porque no puede ser completo.

## 3. RECOMENDACIÓN — descomponer la fila en seis preguntas con umbral propio

En vez de «un veredicto por fila, y Alberto lo firma», **seis preguntas por documento, cada una con
su acierto medido y su propio umbral de auto-aplicación**. Alberto sólo ve las que caen por debajo.

| # | pregunta | regla | quién la puede contestar hoy | acierto medido |
|---|---|---|---|---|
| **Q1** | ¿cuál es la grafía canónica? | R8 | el juez | **14/15 (93%)** en P1 |
| **Q2** | ¿es un producto, o es otra cosa? (norma · fabricante · código de doc · **software**) | R10, R14 | **detector determinista** + juez | sin medir |
| **Q3** | ¿cuántos modelos hay? ¿el cuerpo enumera variantes? | R9 | **detector de sección** + lectura dirigida | sin medir |
| **Q4** | ¿de quién cuelga? (accesorio · familia · sistema anfitrión) | R13, R15, R16, R17 | juez con el catálogo delante | sin medir |
| **Q5** | ¿debe este documento estar en el corpus? | R11 | **detector de higiene** | sin medir |
| **Q6** | ¿hay más identificadores en la portada? | R12 | **extractor de portada** | sin medir |

Las tres marcadas en negrita son **deterministas**: no son un modelo opinando, son un `grep` sobre el
documento. Q2 detecta `EN 54`, `NF S`, `BS 5839`, `ISO 8201`… y dice «esto es una norma, jamás un
producto». Q3 busca «Descripción general», «Modelos», «Ordering Information», el pie de una tabla —
y si los encuentra, **obliga a citarlos**; si no, lo declara. Q5 censa las cuatro clases de documento
sin contenido técnico.

Las tres deterministas cubren **4 de los 6 fallos de P1** y **4 de los 5 de P3**.

**Por qué esto es BP, estructural y escalable, en una frase cada uno:**

- **BP**: cada sub-pregunta tiene un acierto medible por separado, así que la auto-aplicación se
  calibra donde hay evidencia (Q1 hoy, con 93%) y se queda quieta donde no la hay. Un veredicto
  monolítico no se puede calibrar: no se sabe qué parte falló.
- **Estructural**: ataca la raíz medida —incompletitud— y no el síntoma. Un juez mejor leyendo la
  misma portada comete el mismo fallo: el re-juicio **K=5 cross-model** de `spectrex:40-40l`
  convergió **5/5** en el veredicto equivocado, porque la respuesta estaba en la §1.1 y nadie la
  abrió. Más modelo no arregla no-haber-mirado.
- **Escalable a 30+ fabricantes**: los detectores son reglas sobre la FORMA de un documento técnico
  (tiene sección de modelos, cita normas, es una hoja de instalación), no sobre una marca. La única
  parte que crece con el fabricante es Q4, y crece contra el catálogo, que ya escala.

### El orden en que lo haría, por relación valor/riesgo

**Nivel 0 — agrupar por id. Mecánico, riesgo cero, hoy.**
Se lleva el **40%** del esfuerzo de Alberto sin tocar ningún clasificador. `morley:tg` se le preguntó
**15 veces**. Ningún modelo mejor evita eso; lo evita un `groupby`.

**Nivel 1 — los tres detectores deterministas (Q2, Q3, Q5).**
Baratos, auditables, sin LLM. **Primero se miden** (precisión y recall sobre los 69 documentos sin
`doc_map`, que son población real y acotada) y sólo entonces se enchufan. Su salida no es un
veredicto: es **enriquecimiento de la fila** («este doc tiene sección de modelos en la p.9 — léela»).
Enriquecer no puede escribir nada mal.

**Nivel 2 — auto-aplicar SÓLO Q1 (grafía), y sólo con muestra de auditoría.**
Es la única con acierto medido suficiente (93%). Se aplica en bloque, Alberto ve una muestra
aleatoria de 5 y la lista completa, y el gate ya trae CAS + backup para revertir. Umbral re-medido
cada ronda contra su propia población.

**Nivel 3 — validación contra la web del fabricante (R18), acotada.**
Es lo que Alberto hizo a mano 4 veces en su pasada y lo que resolvió los 3 casos más difíciles de
esta sesión. No es «navegar»: es **buscar la ficha del token y comparar N especificaciones**. El caso
`D838` es la prueba de que funciona y de que discrimina: las ocho especificaciones del documento
coinciden **literalmente** con la hoja publicada de WMSOU (System Sensor) y **no** con las de sus
hermanos rebrandeados (KAC `WSO-`, Notifier Opal `NFX-WS-`), que dan 95 dB(A) en vez de 100 e
IP21C/IP44 en vez de IP24/IP65. Un juez leyendo sólo el PDF no podía llegar ahí.

**El humano NO desaparece en ningún nivel** — es requisito explícito de Alberto y además es lo que
DEC-261 demostró que hace falta: una nota suya mal ubicada produjo 6 atestaciones equivocadas. Lo que
cambia es **qué se le pide**: hoy adjudica fila a fila; con esto audita muestras y decide sólo lo que
ningún detector puede decidir.

---

## 4. Alternativas consideradas y por qué se descartan

1. **Un juez mejor o más caro.** Descartada por la medida: el re-juicio K=5 cross-model
   (3× sonnet-5 + 2× gpt-5.5) convergió **5/5 en el veredicto equivocado** de `spectrex:40-40l`. Los
   fallos no son varianza del juez, son preguntas que nadie hizo. Escalar el modelo escala el mismo
   punto ciego.
2. **Afinar (fine-tune) un modelo con las anotaciones de Alberto.** Descartada por dos motivos: 34
   decisiones no son un conjunto de entrenamiento, son un conjunto de REGLAS —y como reglas ya están
   escritas y son legibles—; y un modelo afinado no se puede auditar fila a fila, que es justo lo que
   el gate exige.
3. **Auto-aplicar todos los patrones firmados.** Era mi propuesta inicial. La mata su propia medida:
   P1 60%, P3 44%.
4. **Automatizar sin humano.** Contra el encargo explícito («aunque siempre haya alguien que lo
   valide») y contra la evidencia de DEC-261.
5. **Un CMS/base de datos aparte para los modelos.** Descartada al construir la Wiki: el catálogo
   gobernado YA es esa base y es lo que el bot consulta. Una segunda copia diverge; por eso
   `/catalogo` es una VISTA de sólo lectura sobre los mismos `jsonl`, no un almacén nuevo.
6. **Atacar primero los 601 candidates en cuarentena** (parece el número gordo). Descartada por
   orden: los 69 documentos sin `doc_map` son población acotada y con dueño; los candidates se
   desbloquean solos en gran parte —**184 de los 245 documentos huérfanos** lo son únicamente porque
   todos sus ids siguen en cuarentena—. Medir los detectores sobre 69 es barato; sobre 601, no.

---

## 5. Gaps y riesgos, declarados de entrada

1. **Cinco de las seis sub-preguntas NO tienen acierto medido.** Sólo Q1 lo tiene (93%, n=15, que es
   una n pequeña). Todo el Nivel 1 es «propongo medir», no «propongo enchufar».
2. **n=15, n=9, n=7.** Las tasas de P1/P3/P4 salen de poblaciones diminutas. P4 al 100% con n=7 no
   autoriza a auto-aplicar P4: autoriza a medirlo en la siguiente ronda con más filas.
3. **R13 no se puede cablear**: `relations.jsonl` no tiene tipo `accessory-of`. Es un cambio de
   esquema y bloquea dos filas ya adjudicadas (`kidde:ke-dba-sktw`, `spectrex:40-40-air`).
4. **TECH_DEBT #97 sigue abierto**: `product_model` y `manufacturer` no son persistentes — una
   re-ingesta los deshace en silencio. Cualquier detector que se apoye en `product_model` construye
   sobre arena. Los detectores propuestos leen el CONTENIDO, no la etiqueta, precisamente por esto.
5. **No he medido el coste marginal de un documento nuevo**, que es la magnitud que de verdad importa
   para «a medida que añadimos fabricantes». Sé cuánto queda de backlog (69) pero no cuánto cuesta el
   documento 1.053. Sin ese número, «minimizar el trabajo manual» no tiene denominador.
6. **La clasificación de «acuerdo» del censo es mía y es tosca**: cuenta como acuerdo cualquier nota
   que empiece por «OK», y Alberto escribió «casi OK con juez» seguido de una corrección. Es
   deliberadamente generoso con el sistema: la tasa real de acierto es **igual o peor** que la
   medida, nunca mejor.
7. **Riesgo de la propia descomposición**: seis preguntas por documento es más superficie de la que
   hay hoy. Si cada una llama a un modelo, el coste por documento se multiplica. Mitigación
   propuesta: las tres deterministas no cuestan tokens, y las otras tres caben en una sola llamada
   con salida estructurada — pero eso también está **sin medir**.
